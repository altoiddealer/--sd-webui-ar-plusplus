import contextlib
from pathlib import Path

import gradio as gr

import modules.scripts as scripts
from modules.ui_components import ToolButton

from fractions import Fraction
from math import gcd, sqrt

BASE_PATH = scripts.basedir()
CALCULATOR_SYMBOL = "\U0001F4D0"  # 📐
SWITCH_VALUES_SYMBOL = "\U000021C5"  # ⇅
DIMENSIONS_SYMBOL = "\u2B07\ufe0f"  # ⬇️
IMAGE_DIMENSIONS_SYMBOL = "\U0001F5BC"  # 🖼
REVERSE_LOGIC_SYMBOL = "\U0001F503"  # 🔃
ROUND_SYMBOL = "\U0001F50D"  # 🔍
IMAGE_ROUNDING_MULTIPLIER = 4

is_reverse_logic_mode = False  # FIXME: Global value


class ResButton(ToolButton):
    def __init__(self, res=(512, 512), **kwargs):
        super().__init__(**kwargs)

        self.w, self.h = res

    def reset(self):
        return [self.w, self.h]


# Helper functions for calculating new width/height from aspect ratio
def round_to_precision(val, prec):
    return round(val / prec) * prec

def res_to_model_fit(w, h, mp_target):
    mp = w * h
    scale = sqrt(mp_target / mp)
    w = int(round_to_precision(w * scale, 64))
    h = int(round_to_precision(h * scale, 64))
    return w, h

def dims_from_ar(avg, ar):
    mp_target = avg*avg
    doubleavg = avg*2

    ar_parts = tuple(map(Fraction, ar.split(':')))
    ar_sum = ar_parts[0]+ar_parts[1]
    # calculate width and height by factoring average with aspect ratio
    w = round((ar_parts[0]/ar_sum)*doubleavg)
    h = round((ar_parts[1]/ar_sum)*doubleavg)
    # Round to correct megapixel precision
    w, h = res_to_model_fit(w, h, mp_target)
    return w, h


class ARButton(ToolButton):
    def __init__(self, ar='1/1', **kwargs):
        super().__init__(**kwargs)

        self.ar = ar

    def apply(self, w, h):
        avg = (w + h) // 2
        if (w + h) % 2 != 0: avg += 1
        w, h = dims_from_ar(avg, self.ar)
        return list(map(round, [w, h]))

    def reset(self, w, h):
        return [self.res, self.res]


def parse_aspect_ratios_file(filename):
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

        label, value = line.strip().split(",")
        comment = ""
        if "#" in value:
            value, comment = value.split("#")

        labels.append(label)
        values.append(eval(value))
        comments.append(comment)

    return labels, values, comments


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
        "3:2, 3/2      # Photography\n",
        "4:3, 4/3      # Television photography\n",
        "16:9, 16/9    # Television photography\n",
        "1.85:1, 1.85  # Cinematography\n",
        "2.39:1, 2.39  # Cinematography",
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
    content = [
        "// Do not put custom titles here. This file is overwritten each time the WebUI is started.\n"
    ]
    content.append("arsp__ar_button_titles = {\n")
    counter = 0
    while counter < len(button_titles[0]):
        content.append(
            f'    "{button_titles[0][counter]}" : "{button_titles[1][counter]}",\n'
        )
        counter = counter + 1
    content.append("}")

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(content)


def get_reduced_ratio(n, d):
    n, d = list(map(int, (n, d)))

    if n == d:
        return "1:1"

    if n < d:
        div = gcd(d, n)
    else:
        div = gcd(n, d)

    w = int(n) // div
    h = int(d) // div

    if w == 8 and h == 5:
        w = 16
        h = 10

    return f"{w}:{h}"


def solve_aspect_ratio(w, h, n, d):
    if w != 0 and w:
        return round(w / (n / d))
    elif h != 0 and h:
        return round(h * (n / d))
    else:
        return 0


class AspectRatioScript(scripts.Script):
    def read_aspect_ratios(self):
        ar_file = Path(BASE_PATH, "aspect_ratios.txt")
        if not ar_file.exists():
            write_aspect_ratios_file(ar_file)

        (
            self.aspect_ratio_labels,
            aspect_ratios,
            self.aspect_ratio_comments,
        ) = parse_aspect_ratios_file("aspect_ratios.txt")
        self.aspect_ratios = list(map(float, aspect_ratios))

        # TODO: check for duplicates

        # TODO: check for invalid values

        # TODO: use comments as tooltips
        # see https://github.com/alemelis/sd-webui-ar/issues/5

    def read_resolutions(self):
        res_file = Path(BASE_PATH, "resolutions.txt")
        if not res_file.exists():
            write_resolutions_file(res_file)

        self.res_labels, res, self.res_comments = parse_resolutions_file(
            "resolutions.txt"
        )
        self.res = [list(map(int, r)) for r in res]

    def title(self):
        return "Aspect Ratio picker"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with gr.Column(
            elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_container_aspect_ratio'
        ):
            self.read_aspect_ratios()
            with gr.Row(
                elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_row_aspect_ratio'
            ):
                arc_show_logic = ToolButton(
                    value=REVERSE_LOGIC_SYMBOL,
                    visible=True,
                    variant="secondary",
                    elem_id="arsp__arc_show_logic_button",
                )
                arc_hide_logic = ToolButton(
                    value=REVERSE_LOGIC_SYMBOL,
                    visible=False,
                    variant="primary",
                    elem_id="arsp__arc_hide_logic_button",
                )

                # Aspect Ratio buttons
                ar_btns = [
                    ARButton(ar=label, value=label)
                    for ar, label in zip(
                        self.aspect_ratios,
                        self.aspect_ratio_labels,
                    )
                ]

                with contextlib.suppress(AttributeError):
                    for b in ar_btns:
                        if is_img2img:
                            resolution = [self.i2i_w, self.i2i_h]
                        else:
                            resolution = [self.t2i_w, self.t2i_h]

                        b.click(
                            b.apply,
                            inputs=resolution,
                            outputs=resolution,
                        )

            self.read_resolutions()
            with gr.Row(
                elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_row_resolutions'
            ):
                # Toggle calculator display button
                arc_show_calculator = ToolButton(
                    value=CALCULATOR_SYMBOL,
                    visible=True,
                    variant="secondary",
                    elem_id="arsp__arc_show_calculator_button",
                )
                arc_hide_calculator = ToolButton(
                    value=CALCULATOR_SYMBOL,
                    visible=False,
                    variant="primary",
                    elem_id="arsp__arc_hide_calculator_button",
                )

                btns = [
                    ResButton(res=res, value=label)
                    for res, label in zip(self.res, self.res_labels)
                ]
                with contextlib.suppress(AttributeError):
                    for b in btns:
                        if is_img2img:
                            resolution = [self.i2i_w, self.i2i_h]
                        else:
                            resolution = [self.t2i_w, self.t2i_h]

                        b.click(
                            b.reset,
                            outputs=resolution,
                        )

            # Write button_titles.js with labels and comments read from aspect ratios and resolutions files
            button_titles = [self.aspect_ratio_labels + self.res_labels]
            button_titles.append(self.aspect_ratio_comments + self.res_comments)
            write_js_titles_file(button_titles)

            # dummy components needed for JS function
            dummy_text1 = gr.Text(visible=False)
            dummy_text2 = gr.Text(visible=False)
            dummy_text3 = gr.Text(visible=False)
            dummy_text4 = gr.Text(visible=False)

            # Aspect Ratio Calculator
            with gr.Column(
                visible=False, variant="panel", elem_id="arsp__arc_panel"
            ) as arc_panel:
                arc_title_heading = gr.Markdown(value="#### Aspect Ratio Calculator")
                with gr.Row():
                    with gr.Column(min_width=150):
                        arc_width1 = gr.Number(label="Width 1")
                        arc_height1 = gr.Number(label="Height 1")

                    with gr.Column(min_width=150):
                        arc_desired_width = gr.Number(label="Width 2")
                        arc_desired_height = gr.Number(label="Height 2")

                    with gr.Column(min_width=150):
                        arc_ar_display = gr.Markdown(value="Aspect Ratio:", elem_id="arsp__arc_ar_display_text")
                        with gr.Row(
                            elem_id=f'arsp__{"img" if is_img2img else "txt"}2img_arc_tool_buttons'
                        ):
                            # Switch resolution values button
                            arc_swap = ToolButton(value=SWITCH_VALUES_SYMBOL)
                            arc_swap.click(
                                lambda w, h, w2, h2: (h, w, h2, w2),
                                inputs=[
                                    arc_width1,
                                    arc_height1,
                                    arc_desired_width,
                                    arc_desired_height,
                                ],
                                outputs=[
                                    arc_width1,
                                    arc_height1,
                                    arc_desired_width,
                                    arc_desired_height,
                                ],
                            )
                            with contextlib.suppress(AttributeError):
                                if is_img2img:
                                    resolution = [self.i2i_w, self.i2i_h]
                                    arc_get_img2img_dim = ToolButton(
                                        value=DIMENSIONS_SYMBOL
                                    )
                                    arc_get_img2img_dim.click(
                                        lambda w, h: (w, h),
                                        inputs=resolution,
                                        outputs=[arc_width1, arc_height1],
                                    )
                                else:
                                    resolution = [self.t2i_w, self.t2i_h]
                                    arc_get_txt2img_dim = ToolButton(
                                        value=DIMENSIONS_SYMBOL
                                    )
                                    arc_get_txt2img_dim.click(
                                        lambda w, h: (w, h),
                                        inputs=resolution,
                                        outputs=[arc_width1, arc_height1],
                                    )

                            arc_round = ToolButton(value=ROUND_SYMBOL)

                            if is_img2img:
                                with contextlib.suppress(AttributeError):
                                    # Javascript function to select image element from current img2img tab
                                    current_tab_image = """
                                        function current_tab_image(...args) {
                                            const tab_index = get_img2img_tab_index();
                                            // Get current tab's image (on Batch tab, use image from img2img tab)
                                            if (tab_index == 5) {
                                                image = args[0];
                                            } else {
                                                image = args[tab_index];
                                            }
                                            // On Inpaint tab, select just the image and drop the mask
                                            if (tab_index == 2 && image !== null) {
                                                image = image["image"];
                                            }
                                            return [image, null, null, null, null];
                                        }

                                    """

                                    # Get image dimensions
                                    def get_dims(
                                        img: list,
                                        dummy_text1,
                                        dummy_text2,
                                        dummy_text3,
                                        dummy_text4,
                                    ):
                                        if img:
                                            width = img.size[0]
                                            height = img.size[1]
                                            return width, height
                                        else:
                                            return 0, 0

                                    # Get image dimensions button
                                    arc_get_image_dim = ToolButton(
                                        value=IMAGE_DIMENSIONS_SYMBOL
                                    )
                                    arc_get_image_dim.click(
                                        fn=get_dims,
                                        inputs=self.image,
                                        outputs=[arc_width1, arc_height1],
                                        _js=current_tab_image,
                                    )

                    # Update aspect ratio display on change
                    arc_width1.change(
                        lambda w, h: (f"Aspect Ratio: **{get_reduced_ratio(w,h)}**"),
                        inputs=[arc_width1, arc_height1],
                        outputs=[arc_ar_display],
                    )
                    arc_height1.change(
                        lambda w, h: (f"Aspect Ratio: **{get_reduced_ratio(w,h)}**"),
                        inputs=[arc_width1, arc_height1],
                        outputs=[arc_ar_display],
                    )

                with gr.Row():
                    # Calculate and Apply buttons
                    arc_calc_height = gr.Button(value="Calculate Height", scale=1)
                    arc_calc_height.click(
                        lambda w2, w1, h1: (solve_aspect_ratio(w2, 0, w1, h1)),
                        inputs=[arc_desired_width, arc_width1, arc_height1],
                        outputs=[arc_desired_height],
                    )
                    arc_calc_width = gr.Button(value="Calculate Width", scale=1)
                    arc_calc_width.click(
                        lambda h2, w1, h1: (solve_aspect_ratio(0, h2, w1, h1)),
                        inputs=[arc_desired_height, arc_width1, arc_height1],
                        outputs=[arc_desired_width],
                    )
                    arc_apply_params = gr.Button(value="Apply")
                    with contextlib.suppress(AttributeError):
                        if is_img2img:
                            resolution = [self.i2i_w, self.i2i_h]
                        else:
                            resolution = [self.t2i_w, self.t2i_h]

                        arc_apply_params.click(
                            lambda w2, h2: (w2, h2),
                            inputs=[arc_desired_width, arc_desired_height],
                            outputs=resolution,
                        )

            def _arc_show_logic_update():
                global is_reverse_logic_mode
                is_reverse_logic_mode = not is_reverse_logic_mode

                return [
                    arc_show_logic.update(visible=False),
                    arc_hide_logic.update(visible=True),
                ]

            def _arc_hide_logic_update():
                global is_reverse_logic_mode
                is_reverse_logic_mode = not is_reverse_logic_mode

                return [
                    arc_show_logic.update(visible=True),
                    arc_hide_logic.update(visible=False),
                ]

            arc_round.click(
                lambda w, h: (
                    round_to_multiple(w, multiple=IMAGE_ROUNDING_MULTIPLIER),
                    round_to_multiple(h, multiple=IMAGE_ROUNDING_MULTIPLIER),
                ),
                inputs=[arc_desired_width, arc_desired_height],
                outputs=[arc_desired_width, arc_desired_height],
            )

            # Show calculator pane (and reset number input values)
            arc_show_calculator.click(
                lambda: [
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(value=512),
                    gr.update(value=512),
                    gr.update(value=0),
                    gr.update(value=0),
                    gr.update(value="Aspect Ratio: **1:1**"),
                ],
                None,
                [
                    arc_panel,
                    arc_show_calculator,
                    arc_hide_calculator,
                    arc_width1,
                    arc_height1,
                    arc_desired_width,
                    arc_desired_height,
                    arc_ar_display,
                ],
            )
            # Hide calculator pane
            arc_hide_calculator.click(
                lambda: [
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False),
                ],
                None,
                [arc_panel, arc_show_calculator, arc_hide_calculator],
            )

            arc_show_logic.click(
                _arc_show_logic_update,
                None,
                [arc_show_logic, arc_hide_logic],
            )
            arc_hide_logic.click(
                _arc_hide_logic_update,
                None,
                [arc_show_logic, arc_hide_logic],
            )


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


def round_to_multiple(x, multiple):
    return multiple * round(x / multiple)
