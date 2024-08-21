import typing as t
import contextlib
from pathlib import Path

import gradio as gr

import modules.scripts as scripts
from modules.ui_components import ToolButton

from fractions import Fraction
from math import sqrt

BASE_PATH = scripts.basedir()

class ButtonState():
    def __init__(self):
        self.is_locked = False
        self.switched = False
        self.alt_mode = False
    def toggle_lock(self):
       self.is_locked = not self.is_locked
    def toggle_switch(self):
        self.switched = not self.switched
    def toggle_mode(self):
        self.alt_mode = not self.alt_mode

txt2img_state = ButtonState()
img2img_state = ButtonState()

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

## Aspect Ratio buttons
def create_ar_button_function(ar:str, is_img2img:bool):
    def wrapper(avg, prec, w=512, h=512):
        # Determine the state based on whether it's img2img or txt2img
        state = img2img_state if is_img2img else txt2img_state
        
        n, d = map(Fraction, ar.split(':'))  # Split numerator and denominator
        
        if not state.is_locked:
            avg = avg_from_dims(w, h)  # Get average of current width/height values
        
        if not state.alt_mode:  # True = offset, False = One dimension
            w, h = dims_from_ar(avg, n, d, prec)  # Calculate new w + h from avg, AR, and precision
            if state.switched:  # Switch results if switch mode is active
                w, h = h, w
        else:  # Calculate w or h from input, AR, and precision
            if state.switched:  # Switch results if switch mode is active
                w, h = calc_width(n, d, w, h, prec)  # Modify width
            else:
                w, h = calc_height(n, d, w, h, prec)  # Modify height

        return avg, w, h

    return wrapper

def create_ar_buttons(
    lst: t.Iterable[str],
    is_img2img: bool,
) -> t.Tuple[t.List[ToolButton], t.Dict[ToolButton, t.Callable]]:
    buttons = []
    functions = {}

    for ar in lst:
        button = ToolButton(ar, render=False)
        function = create_ar_button_function(ar, is_img2img)
        buttons.append(button)
        functions[button] = function

    return buttons, functions

## Static Resolution buttons
def create_res_button_function(w:int, h:int, is_img2img:bool):
    def wrapper(avg):
        state = img2img_state if is_img2img else txt2img_state
        if not state.is_locked:
            avg = avg_from_dims(w, h)
        return avg, w, h
    return wrapper

def create_res_buttons(
    lst: t.Iterable[t.Tuple[t.List[int], str]],
    is_img2img: bool,
) -> t.Tuple[t.List[ToolButton], t.Dict[ToolButton, t.Callable]]:
    buttons = []
    functions = {}

    for resolution, label in lst:
        button = ToolButton(label)
        w, h = resolution
        function = create_res_button_function(w, h, is_img2img)
        buttons.append(button)
        functions[button] = function

    return buttons, functions

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
        self.ar_buttons_labels = self.aspect_ratios

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

        # Determine the width and height based on the mode (img2img or txt2img)
        if is_img2img:
            w = self.i2i_w
            h = self.i2i_h
        else:
            w = self.t2i_w
            h = self.t2i_h

        # Average number box initialize without rendering
        arc_average = gr.Number(label="Current W/H Avg.", value=0, interactive=False, render=False)

        # Precision input box initialize without rendering
        arc_prec = gr.Number(label="Precision (px)", value=64, minimum=4, maximum=128, step=4, precision=0, render=False)

        with gr.Accordion(label="Aspect Ratio and Resolution Buttons", open=True):

            with gr.Column(elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_container_aspect_ratio'):

                # Get aspect ratios from file
                self.read_aspect_ratios()

                # Top row
                with gr.Row(elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_row_aspect_ratio'):

                    # Lock button
                    arc_lock = ToolButton(value=self.LOCK_OPEN_ICON, visible=True, variant="secondary", elem_id="arsp__arc_lock_button")
                    # Lock button click event handling
                    def toggle_lock(icon, avg, w=512, h=512):
                        icon = self.LOCK_OPEN_ICON if (img2img_state.is_locked if is_img2img else txt2img_state.is_locked) else self.LOCK_CLOSED_ICON
                        if is_img2img:
                            img2img_state.toggle_lock()
                        else:
                            txt2img_state.toggle_lock()
                        if not avg:
                            avg = avg_from_dims(w, h)
                        return icon, avg
                    if is_img2img:
                        lock_w = self.i2i_w
                        lock_h = self.i2i_h
                    else:
                        lock_w = self.t2i_w
                        lock_h = self.t2i_h
                    # Lock button event listener
                    arc_lock.click(toggle_lock,
                                   inputs = [arc_lock, arc_average, lock_w, lock_h],
                                   outputs = [arc_lock, arc_average],
                                   show_progress = 'hidden')

                    # Initialize Aspect Ratio buttons (render=False)
                    ar_buttons, ar_functions = create_ar_buttons(self.ar_buttons_labels, is_img2img)

                    # Switch button
                    arc_switch = ToolButton(value=self.LAND_AR_ICON, visible=True, variant="secondary", elem_id="arsp__arc_switch_button")
                    # Switch button click event handling
                    def toggle_switch(*items, **kwargs):
                        ar_icons = items[:-1]
                        sw_icon = items[-1]  
                        if ar_icons == tuple(self.aspect_ratios):
                            ar_icons = tuple(self.flipped_vals)
                        else:
                            ar_icons = tuple(self.aspect_ratios)
                        sw_icon = self.PORT_AR_ICON if sw_icon == self.LAND_AR_ICON else self.LAND_AR_ICON
                        if is_img2img:
                            img2img_state.toggle_switch()
                        else:
                            txt2img_state.toggle_switch()
                        return (*ar_icons, sw_icon)
                    # Switch button event listener
                    arc_switch.click(toggle_switch,
                                     inputs = ar_buttons+[arc_switch],
                                     outputs = ar_buttons+[arc_switch])

                    # AR buttons render
                    for button in ar_buttons:
                        button.render()
                    # AR buttons click event handling
                    with contextlib.suppress(AttributeError):
                        for button in ar_buttons:                            
                            # AR buttons event listener
                            button.click(ar_functions[button],
                                         inputs = [arc_average, arc_prec, w, h],
                                         outputs = [arc_average, w, h],
                                         show_progress = 'hidden')

                # Get static resolutions from file
                self.read_resolutions()

                # Bottom row
                with gr.Row(elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_row_resolutions'):

                    # Info button to toggle info window
                    arc_show_info = ToolButton(value=self.INFO_ICON, visible=True, variant="secondary", elem_id="arsp__arc_show_info_button")
                    arc_hide_info = ToolButton(value=self.INFO_CLOSE_ICON, visible=False, variant="secondary", elem_id="arsp__arc_hide_info_button")
                    ### Click event handling for info window ###
                    ##### is defined after everything else #####

                    # Mode button
                    arc_mode = ToolButton(value=self.OFFSET_ICON, visible=True, variant="secondary", elem_id="arsp__arc_mode_button")
                    # Mode button click event handling
                    def toggle_mode(icon):
                        icon = self.ONE_DIM_ICON if icon == self.OFFSET_ICON else self.OFFSET_ICON
                        if is_img2img:
                            img2img_state.toggle_mode()
                        else:
                            txt2img_state.toggle_mode()
                        return icon
                    # Mode button event listener
                    arc_mode.click(toggle_mode,
                                   inputs = [arc_mode],
                                   outputs = [arc_mode])

                    # Static res buttons
                    buttons, set_res_functions = create_res_buttons(zip(self.res, self.res_labels), is_img2img)

                    # Set up click event listeners for the buttons
                    with contextlib.suppress(AttributeError):
                        for button in buttons:
                            button.click(set_res_functions[button],
                                         inputs = [arc_average],
                                         outputs = [arc_average, w, h],
                                         show_progress = 'hidden')

                # Write button_titles.js with labels and comments read from aspect ratios and resolutions files
                button_titles = [self.aspect_ratios + self.res_labels]
                button_titles.append(self.aspect_ratio_comments + self.res_comments)
                write_js_titles_file(button_titles)
                
                # Information panel
                with gr.Column(visible=False, variant="panel", elem_id="arsp__arc_panel") as arc_panel:
                    with gr.Row():
                        with gr.Column(scale=2, min_width=100):

                            # Average number box render
                            arc_average.render()

                            # Precision input box render
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

                # Info panel event listeners
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
