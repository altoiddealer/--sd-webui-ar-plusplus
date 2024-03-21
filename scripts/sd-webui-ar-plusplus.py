import contextlib
from pathlib import Path

import gradio as gr

import modules.scripts as scripts
from modules.ui_components import ToolButton

from fractions import Fraction
from math import gcd, sqrt

BASE_PATH = scripts.basedir()

is_locked = False

# Helper functions for calculating new width/height values
def round_to_precision(val, prec):
    return round(val / prec) * prec

def res_to_model_fit(avg, w, h, prec):
    mp = w * h
    mp_target = avg * avg
    scale = sqrt(mp_target / mp)
    w = int(round_to_precision(w * scale, prec))
    h = int(round_to_precision(h * scale, prec))
    return w, h

def calc_width(n, d, w, h, prec):
    ar = round((n / d), 2) # Convert AR parts to fraction
    if ar > 1.0:
        h = w / ar
    elif ar < 1.0:
        w = h * ar
    else:
        new_value = max([w, h])
        w, h = new_value, new_value
    w = int(round_to_precision((w + prec / 2), prec))
    h = int(round_to_precision((h + prec / 2), prec))
    return w, h

def calc_height(n, d, w, h, prec):
    ar = round((n / d), 2) # Convert AR parts to fraction
    if ar > 1.0:
        w = h * ar
    elif ar < 1.0:
        h = w / ar
    else:
        new_value = min([w, h])
        w, h = new_value, new_value
    w = int(round_to_precision((w + prec / 2), prec))
    h = int(round_to_precision((h + prec / 2), prec))
    return w, h

def dims_from_ar(avg, n, d, prec):
    doubleavg = avg * 2
    ar_sum = n+d
    # calculate width and height by factoring average with aspect ratio
    w = round((n / ar_sum) * doubleavg)
    h = round((d / ar_sum) * doubleavg)
    # Round to correct megapixel precision
    w, h = res_to_model_fit(avg, w, h, prec)
    return w, h

def avg_from_dims(w, h):
    avg = (w + h) // 2
    if (w + h) % 2 != 0:
        avg += 1
    return avg

# Aspect Ratio buttons
class ARButton(ToolButton):
    switched = False
    alt_mode = False

    def __init__(self, value='1:1', **kwargs):
        super().__init__(**kwargs)
        self.value = value

    def apply(self, avg, prec, w=512, h=512):
        ar = self.value
        n, d = map(Fraction, ar.split(':'))         # split numerator and denominator
        if not is_locked:
            avg = avg_from_dims(w, h)               # Get average of current width/height values
        if not ARButton.alt_mode:                           # True = offset, False = One dimension
            w, h = dims_from_ar(avg, n, d, prec)    # Calculate new w + h from avg, AR, and precision
            if ARButton.switched:                   # Switch results if switch mode active
                w, h = h, w
        else:                                       # Calculate w or h from input, AR, and precision
            if ARButton.switched:                   # Switch results if switch mode active
                w, h = calc_width(n, d, w, h, prec)     # Modify width
            else:
                w, h = calc_height(n, d, w, h, prec)    # Modify height
        return avg, w, h

    @classmethod
    def toggle_switch(cls):
        cls.switched = not cls.switched

    @classmethod
    def toggle_mode(cls):
        cls.alt_mode = not cls.alt_mode

# Static Resolution buttons
class ResButton(ToolButton):
    def __init__(self, res=(512, 512), **kwargs):
        super().__init__(**kwargs)
        self.w, self.h = res

    def reset(self, avg):
        # Get average of current width/height values
        if not is_locked:
            avg = avg_from_dims(self.w, self.h)
        return avg, self.w, self.h

# Get values for Aspect Ratios from file
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
        value = value.strip()
        values.append(value)
        comments.append(comment)

        comp1, comp2 = value.split(':')
        flipval = f"{comp2}:{comp1}"
        flipvals.append(flipval)

    return values, comments, flipvals


# Get values for Static Resolutions from file
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

def write_aspect_ratios_file(filename):
    aspect_ratios = [
        "1:1            # Square\n",
        "4:3            # Television Photography\n",
        "3:2            # Photography\n",
        "8:5            # Widescreen Displays\n",
        "16:9           # Widescreen Television\n",
        "21:9           # Ultrawide Cinematography"
    ]
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(aspect_ratios)

def write_resolutions_file(filename):
    resolutions = [
        "512, 512, 512     # 512x512\n",
        "768, 768, 768     # 768x768\n",
        "1024, 1024, 1024  # 1024x1024\n",
        "1280, 1280, 1280  # 1280x1280\n",
        "1536, 1536, 1536  # 1536x1536\n",
        "2048, 2048, 2048  # 2048x2048",
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
        self.LOCK_OPEN_ICON = "\U0001F513"      # 🔓
        self.LOCK_CLOSED_ICON = "\U0001F512"    # 🔒
        self.LAND_AR_ICON = "\U000025AD"        # ▭
        self.PORT_AR_ICON = "\U000025AF"        # ▯
        self.INFO_ICON = "\U00002139"           # ℹ
        self.INFO_CLOSE_ICON = "\U00002BC5"     # ⯅
        self.OFFSET_ICON = "\U00002B83"         # ⮃
        self.ONE_DIM_ICON = "\U00002B85"        # ⮅

        arc_avg = gr.Number(label="Current W/H Avg.", value=0, interactive=False, render=False)
        arc_prec = gr.Number(label="Precision (px)", value=64, minimum=4, maximum=128, step=4, precision=0, render=False)

        with gr.Accordion(label="Aspect Ratio and Resolution Buttons", open=True):

            with gr.Column(elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_container_aspect_ratio'):

                # Get aspect ratios from file
                self.read_aspect_ratios()

                # Top row
                with gr.Row(elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_row_aspect_ratio'):

                    # Lock button
                    arc_lock = ToolButton(value=self.LOCK_OPEN_ICON, visible=True, variant="secondary", elem_id="arsp__arc_lock_button")
                    # Click event handling for lock button
                    def toggle_lock(icon, avg, w=512, h=512):
                        global is_locked
                        icon = self.LOCK_OPEN_ICON if is_locked else self.LOCK_CLOSED_ICON
                        is_locked = not is_locked
                        if not avg:
                            avg = avg_from_dims(w, h)
                        return icon, avg
                    if is_img2img:
                        lock_w = self.i2i_w
                        lock_h = self.i2i_h
                    else:
                        lock_w = self.t2i_w
                        lock_h = self.t2i_h
                    arc_lock.click(toggle_lock, inputs=[arc_lock, arc_avg, lock_w, lock_h], outputs=[arc_lock, arc_avg])

                    # Initialize Aspect Ratio buttons (render=False)
                    ar_btns = [ARButton(value=ar, render=False) for ar in self.ar_btns_labels]

                    # Switch button
                    arc_sw = ToolButton(value=self.LAND_AR_ICON, visible=True, variant="secondary", elem_id="arsp__arc_sw_button")
                    # Click event handling for switch button
                    def toggle_switch(*items, **kwargs):
                        ar_icons = items[:-1]
                        sw_icon = items[-1]  
                        if ar_icons == tuple(self.aspect_ratios):
                            ar_icons = tuple(self.flipped_vals)
                        else:
                            ar_icons = tuple(self.aspect_ratios)
                        sw_icon = self.PORT_AR_ICON if sw_icon == self.LAND_AR_ICON else self.LAND_AR_ICON
                        ARButton.toggle_switch()
                        return (*ar_icons, sw_icon)

                    arc_sw.click(toggle_switch, inputs=ar_btns+[arc_sw], outputs=ar_btns+[arc_sw])

                    # Render the Aspect Ratio buttons
                    for b in ar_btns:
                        b.render()

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
                    arc_show_info = ToolButton(value=self.INFO_ICON, visible=True, variant="secondary", elem_id="arsp__arc_show_info_button")
                    arc_hide_info = ToolButton(value=self.INFO_CLOSE_ICON, visible=False, variant="secondary", elem_id="arsp__arc_hide_info_button")
                    # Click event handling for info window
                    # Handled after everything else

                    # Mode button
                    arc_mode = ToolButton(value=self.OFFSET_ICON, visible=True, variant="secondary", elem_id="arsp__arc_mode_button")
                    # Click event handling for Mode button
                    def toggle_mode(icon):
                        icon = self.ONE_DIM_ICON if icon == self.OFFSET_ICON else self.OFFSET_ICON
                        ARButton.toggle_mode()
                        return icon
                    arc_mode.click(toggle_mode, inputs=[arc_mode], outputs=[arc_mode])

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
                            **Aspect Ratio buttons (Top Row)**:
                            (1) Averages the current width/height in the UI; (2) Offsets to the exact aspect ratio; (3) Rounds to precision.

                            **Static Resolution buttons (Bottom Row)**:
                            Recommended to use 1:1 values for these, to serve as a start point before clicking AR buttons.

                            **64px Precision is recommended, the same rounding applied for image "bucketing" when model training.**
                            '''
                            )

                # Toggle info panel
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