import contextlib
from pathlib import Path

import gradio as gr

import modules.scripts as scripts
from modules.ui_components import ToolButton

from fractions import Fraction
from math import gcd, sqrt

BASE_PATH = scripts.basedir()
SWITCH_SYMBOL = "\U0001F501"        # 🔁
LOCK_OPEN_SYMBOL = "\U0001F513"     # 🔓
LOCK_SYMBOL = "\U0001F512"          # 🔒
LAND_AR_SYMBOL = "\U000025AD"       # ▭
PORT_AR_SYMBOL = "\U000025AF"       # ▯
INFO_SYMBOL = "\U00002139"          # ℹ

is_lock_mode = False  # FIXME: Global value
is_switch_mode = False  # FIXME: Global value
is_locked = False

## Aspect Ratio buttons
# Helper functions for calculating new width/height from aspect ratio
def round_to_precision(val, prec):
    return round(val / prec) * prec

def res_to_model_fit(w, h, mp_target, prec):
    mp = w * h
    scale = sqrt(mp_target / mp)
    w = int(round_to_precision(w * scale, prec))
    h = int(round_to_precision(h * scale, prec))
    return w, h

def dims_from_ar(avg, ar, prec):
    mp_target = avg*avg
    doubleavg = avg*2

    ar_parts = tuple(map(Fraction, ar.split(':')))
    ar_sum = ar_parts[0]+ar_parts[1]
    # calculate width and height by factoring average with aspect ratio
    w = round((ar_parts[0]/ar_sum)*doubleavg)
    h = round((ar_parts[1]/ar_sum)*doubleavg)
    # Round to correct megapixel precision
    w, h = res_to_model_fit(w, h, mp_target, prec)
    return w, h

def avg_from_dims(w, h):
    avg = (w + h) // 2
    if (w + h) % 2 != 0:
        avg += 1
    return avg

class ARButton(ToolButton):
    switched = False

    def __init__(self, value='1:1', **kwargs):
        super().__init__(**kwargs)
        self.value = value

    def apply(self, avg, prec, w=512, h=512):
        # Get average of current width/height values
        if not is_locked:
            avg = avg_from_dims(w, h)
        # Calculate new w/h from avg, AR, and precision
        w, h = dims_from_ar(avg, self.value, prec)
        if ARButton.switched:
            w, h = h, w # return switched results
        return avg, w, h

    @classmethod
    def toggle_switch(cls):
        cls.switched = not cls.switched

## Static Resolution buttons
class ResButton(ToolButton):
    def __init__(self, res=(512, 512), **kwargs):
        super().__init__(**kwargs)
        self.w, self.h = res

    def reset(self, avg):
        # Get average of current width/height values
        if not is_locked:
            avg = avg_from_dims(self.w, self.h)
        return avg, self.w, self.h

## Get values for Aspect Ratios from file
def parse_aspect_ratios_file(filename):
    values, flipvals, comments = [], [], []
    file = Path(BASE_PATH, filename)

    if not file.exists():
        return values, comments, flipvals

    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return values, comments, flipvals

    for line in lines:
        if line.startswith("#"):
            continue

        value = line.strip()

        comment = ""
        if "#" in value:
            value, comment = value.split("#")
        values.append(value)
        comments.append(comment)

        comp1, comp2 = value.split(':')
        flipval = f"{comp2}:{comp1}"
        flipvals.append(flipval)

    return values, comments, flipvals


## Get values for Static Resolutions from file
def parse_resolutions_file(filename):
    labels, values, comments = [], [], []
    file = Path(BASE_PATH, filename)

    if not file.exists():
        return labels, values, comments

    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return labels, values, comments

    for line in lines:
        if line.startswith("#"):
            continue

        label, width, height = line.strip().split(",")
        comment = ""
        if "#" in height:
            height, comment = height.split("#")

        resolution = (width, height)

        labels.append(label)
        values.append(resolution)
        comments.append(comment)

    return labels, values, comments

# TODO: write a generic function handling both cases
def write_aspect_ratios_file(filename):
    aspect_ratios = [
        "3:2            # Photography\n",
        "4:3            # Television photography\n",
        "16:9           # Television photography\n",
        "1.85:1         # Cinematography\n",
        "2.39:1         # Cinematography",
    ]
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(aspect_ratios)

def write_resolutions_file(filename):
    resolutions = [
        "512, 512, 512     # 512x512\n",
        "640, 640, 640     # 640x640\n",
        "768, 768, 768     # 768x768\n",
        "896, 896, 896     # 896x896\n",
        "1024, 1024, 1024  # 1024x1024",
    ]
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(resolutions)

def write_js_titles_file(button_titles):
    filename = Path(BASE_PATH, "javascript", "button_titles.js")
    content = ["// Do not put custom titles here. This file is overwritten each time the WebUI is started.\n"]
    content.append("arsp__ar_button_titles = {\n")
    counter = 0
    while counter < len(button_titles[0]):
        content.append(f'    " {button_titles[0][counter]}" : "{button_titles[1][counter]}",\n')
        counter = counter + 1
    content.append("}")

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(content)

class AspectRatioScript(scripts.Script):
    def read_aspect_ratios(self):
        ar_file = Path(BASE_PATH, "aspect_ratios.txt")
        if not ar_file.exists():
            write_aspect_ratios_file(ar_file)
        (self.aspect_ratios, self.aspect_ratio_comments, self.flipped_vals) = parse_aspect_ratios_file("aspect_ratios.txt")
        self.ar_btns_labels = self.aspect_ratios

    def read_resolutions(self):
        res_file = Path(BASE_PATH, "resolutions.txt")
        if not res_file.exists():
            write_resolutions_file(res_file)

        self.res_labels, res, self.res_comments = parse_resolutions_file("resolutions.txt")
        self.res = [list(map(int, r)) for r in res]

    def title(self):
        return "Aspect Ratio picker"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        arc_avg = gr.Number(label="Current W/H Avg.", value=0, interactive=False, render=False)
        arc_prec = gr.Number(label="Precision (px)", info='64px is recommended, the same rounding applied for image "bucketing" when model training.', value=64, minimum=4, maximum=128, precision=0, render=False)

        with gr.Column(elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_container_aspect_ratio'):
            # Get aspect ratios from file
            self.read_aspect_ratios()
            # Top row
            with gr.Row(elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_row_aspect_ratio'):

                # Lock button
                arc_show_lock = ToolButton(value=LOCK_SYMBOL, min_width=84, scale = 0, visible=True, variant="secondary", elem_id="arsp__arc_show_lock_button")
                arc_hide_lock = ToolButton(value=LOCK_SYMBOL, min_width=84, scale = 0, visible=False, variant="primary", elem_id="arsp__arc_hide_lock_button")
                # Click event handling for lock button
                def toggle_lock(avg, w=512, h=512):
                    global is_locked
                    is_locked = not is_locked
                    if not avg:
                        avg = avg_from_dims(w, h)
                    return avg
                if is_img2img:
                    lock_w = self.i2i_w
                    lock_h = self.i2i_h
                else:
                    lock_w = self.t2i_w
                    lock_h = self.t2i_h
                arc_show_lock.click(toggle_lock, inputs=[arc_avg, lock_w, lock_h], outputs=[arc_avg])
                arc_hide_lock.click(toggle_lock, inputs=[arc_avg, lock_w, lock_h], outputs=[arc_avg])

                # Switch button
                arc_sw_on = ToolButton(value=SWITCH_SYMBOL, min_width=84, scale = 0, visible=True, variant="secondary", elem_id="arsp__arc_sw_on_button")
                arc_sw_off = ToolButton(value=SWITCH_SYMBOL, min_width=84, scale = 0, visible=False, variant="primary", elem_id="arsp__arc_sw_off_button")
                # Click event handling for switch button
                def toggle_switch():
                    ARButton.toggle_switch()
                # def toggle_switch():
                #     if self.ar_btns_labels == self.aspect_ratios:
                #         self.ar_btns_labels = self.flipped_vals
                #     else:
                #         self.ar_btns_labels = self.aspect_ratios
                arc_sw_on.click(toggle_switch)
                arc_sw_off.click(toggle_switch)

                # Aspect Ratio buttons
                ar_btns = [ARButton(value=ar) for ar in self.ar_btns_labels]
                # Click event handling for AR buttons
                with contextlib.suppress(AttributeError):
                    for b in ar_btns:
                        if is_img2img:
                            w = self.i2i_w
                            h = self.i2i_h
                        else:
                            w = self.t2i_w
                            h = self.t2i_h  
                                                  
                        b.click(b.apply, inputs=[arc_avg, arc_prec, w, h], outputs=[arc_avg, w, h])

            # Get resolutions from file
            self.read_resolutions()
            # Bottom row
            with gr.Row(elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_row_resolutions'):
                # Info button to toggle info window
                arc_show_info = ToolButton(value=INFO_SYMBOL, min_width=84, scale = 1.0, visible=True, variant="secondary", elem_id="arsp__arc_show_info_button")
                arc_hide_info = ToolButton(value=INFO_SYMBOL, min_width=84, scale = 1.0, visible=False, variant="primary", elem_id="arsp__arc_hide_info_button")
                # Click event handling for info window
                def toggle_info():
                    arc_panel.visible = not arc_panel.visible
                    arc_show_info.visible = not arc_show_info.visible
                    arc_hide_info.visible = not arc_hide_info.visible

                arc_show_info.click(toggle_info)
                arc_hide_info.click(toggle_info)

                # Static resolution buttons
                btns = [ResButton(res=res, value=label) for res, label in zip(self.res, self.res_labels)]
                # Click event handling for static res buttons
                with contextlib.suppress(AttributeError):
                    for b in btns:
                        b.click(b.reset, inputs=[arc_avg], outputs=[arc_avg, w, h])

            # Write button_titles.js with labels and comments read from aspect ratios and resolutions files
            button_titles = [self.aspect_ratios + self.res_labels]
            button_titles.append(self.aspect_ratio_comments + self.res_comments)
            write_js_titles_file(button_titles)
            
            # Information panel
            with gr.Column(visible=False, variant="panel", elem_id="arsp__arc_panel") as arc_panel:
                with gr.Row():
                    with gr.Column(scale=2, min_width=100):
                        # render the current average number box
                        arc_avg.render()

                        # render the precision input box
                        arc_prec.render()

                    # Information blurb
                    gr.Column(scale=1, min_width=10)
                    with gr.Column(scale=12):
                        arc_title_heading = gr.Markdown(value=
                        '''
                        ### AR and Static Res buttons can be customized in the 'aspect_ratios.txt' and 'resolutions.txt' files
                        ### Top Row:
                        **Aspect Ratio (AR) buttons** - calculate and apply desireable width/height by: (1) Averaging the current width/height in the UI; (2) Offsetting to the exact AR; (3) Rounding to precision.
                        **Lock button** - captures the current average width/height in the UI. This is good when switching between ARs. When unlocked, the average will change due to rounding.
                        **Switch button** - toggles between landscape and portrait orientation for ease of use.
                        ### Bottom Row:
                        **Static Resolution buttons** - recommended to use 1:1 values for these, to serve as a start point before clicking AR buttons.
                        **Mode button** will change the method of the AR buttons to calculate only one value, rather than offsetting.
                        '''
                        )

            # Show info pane
            arc_show_info.click(
                lambda: [
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=True),
                ],
                None,
                [
                    arc_panel,
                    arc_show_info,
                    arc_hide_info,
                ],
            )
            # Hide info pane
            arc_hide_info.click(
                lambda: [
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False),
                ],
                None,
                [arc_panel, arc_show_info, arc_hide_info],
            )

            def _arc_show_lock_update():
                global is_lock_mode
                is_lock_mode = not is_lock_mode

                return [
                    arc_show_lock.update(visible=False),
                    arc_hide_lock.update(visible=True),
                ]
            def _arc_hide_lock_update():
                global is_lock_mode
                is_lock_mode = not is_lock_mode

                return [
                    arc_show_lock.update(visible=True),
                    arc_hide_lock.update(visible=False),
                ]

            arc_show_lock.click(
                _arc_show_lock_update,
                None,
                [arc_show_lock, arc_hide_lock],
            )
            arc_hide_lock.click(
                _arc_hide_lock_update,
                None,
                [arc_show_lock, arc_hide_lock],
            )

            def _arc_sw_on_update():
                global is_switch_mode
                is_switch_mode = not is_switch_mode

                return [
                    arc_sw_on.update(visible=False),
                    arc_sw_off.update(visible=True),
                ]
            def _arc_sw_off_update():
                global is_switch_mode
                is_switch_mode = not is_switch_mode

                return [
                    arc_sw_on.update(visible=True),
                    arc_sw_off.update(visible=False),
                ]

            arc_sw_on.click(
                _arc_sw_on_update,
                None,
                [arc_sw_on, arc_sw_off],
            )
            arc_sw_off.click(
                _arc_sw_off_update,
                None,
                [arc_sw_on, arc_sw_off],
            )

    ## Function to update the values in appropriate Width/Height fields
    # https://github.com/AUTOMATIC1111/stable-diffusion-webui/pull/7456#issuecomment-1414465888
    def after_component(self, component, **kwargs):
        if kwargs.get("elem_id") == "txt2img_width":
            self.t2i_w = component
        if kwargs.get("elem_id") == "txt2img_height":
            self.t2i_h = component
        if kwargs.get("elem_id") == "img2img_width":
            self.i2i_w = component
        if kwargs.get("elem_id") == "img2img_height":
            self.i2i_h = component
        if kwargs.get("elem_id") == "img2img_image":
            self.image = [component]
        if kwargs.get("elem_id") == "img2img_sketch":
            self.image.append(component)
        if kwargs.get("elem_id") == "img2maskimg":
            self.image.append(component)
        if kwargs.get("elem_id") == "inpaint_sketch":
            self.image.append(component)
        if kwargs.get("elem_id") == "img_inpaint_base":
            self.image.append(component)