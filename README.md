# Stable Diffusion WebUI Aspect Ratio and Resolution Buttons

Extension for [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui.git) and [stable-diffusion-webui-forge](https://github.com/lllyasviel/stable-diffusion-webui-forge) adding image aspect ratio selector buttons.

---

## Main Fork feature

<img width="938" alt="Screenshot 2024-03-13 111328" src="https://github.com/altoiddealer/--sd-webui-ar-plusplus/assets/1613484/67bfba6d-ba08-4a7a-b34f-03fe266bf9d8">

#### Uses an enhanced method to calculate the width/height values when clicking Aspect Ratio buttons.

- Gets the mean value (average) of the current **width** and **height** values in the UI.
  
- For the selected aspect ratio, the dimensions are offset equally (positively and negatively) from the average, ensuring nearest total pixel count to user's initial resolution.
  
- Uses the same precision rounding method as [Stability-AI/StableSwarmUI](https://github.com/Stability-AI/StableSwarmUI/blob/4ef98019fc4796d69f0d1d2dfa487d684a748cc3/src/Utils/Utilities.cs#L573) when updating image dimensions.
  
- "Mode" button allows switching to use calculation method from [LEv145/--sd-webui-ar-plus](https://github.com/LEv145/--sd-webui-ar-plus) (Only update Width OR Height)

---

<img width="944" alt="1" src="https://github.com/altoiddealer/--sd-webui-ar-plusplus/assets/1613484/87a12aef-76f9-450b-a908-49131078b1dd">

---

#### For best results switching between aspect ratios, pick a static res value (such as 1024, etc), then press the "Lock" button to lock in an average res.

- The calculation method works correctly in all cases
  
- However, since the output values are rounded to the nearest division of 64, the mean value (average) of the input values will change when "Unlocked".

---

<img width="937" alt="2" src="https://github.com/altoiddealer/--sd-webui-ar-plusplus/assets/1613484/bb124293-289c-4f8c-b2f6-2e7de060f188">

---

#### The original "Calculator panel" has been replaced with an information panel:

- Current average is displayed for reference.

- Rounding precision can be adjusted with default value of 64px.

---

## Installation

1. Navigate to the Extensions tab in [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui.git) or [stable-diffusion-webui-forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)

2. Click "Install from URL"
   
3. Copy/Paste this repository into the "URL for extension's git repository" field and click "Install"
   ```
   https://github.com/altoiddealer/--sd-webui-ar-plusplus
   ```
   
   <img width="895" alt="install" src="https://github.com/altoiddealer/--sd-webui-ar-plusplus/assets/1613484/21b0ab04-2760-4c91-862e-7b71c7f08feb">

   
4. Return to the "Installed" tab and click "Apply and restart UI"

  <img width="877" alt="Restart" src="https://github.com/altoiddealer/--sd-webui-ar-plusplus/assets/1613484/72a5e77e-b8a2-49a1-9d5f-81524bb18a27">
 

---

<details>

<summary>Details from [the source project (LEv145/--sd-webui-ar-plus)</summary>

# Details from [the source project](https://github.com/LEv145/--sd-webui-ar-plus) (LEv145/--sd-webui-ar-plus)

(For reference - much of this is obsolete)

## Fork features

- New button `🔃` for calculation of height and width inverse
  - Normal mode: `1024x1024 and 16:9 = 1820x1024`
  - Reverse mode: `1024x1024 and 16:9 = 1024x576`
- New button `🔍` for rounding dimensions to the nearest multiples of 4 (`1023x101` => `1024x100`)
- New styles (Some styles have been moved to the original extension)
- Better resolution presets (By formula: `f(x) = 512 + (1024-512)/4*x, 0 <= x <= 4`)
- Better ratios presets (From [wikipedia](https://en.wikipedia.org/wiki/Aspect_ratio_(image)))
- Rename `Calc` button to `📐`
- Can work together with the original extension


## Updates

- 20/02/2023 :warning: this update will remove your local config files (`aspect_ratios.txt` and `resolutions.txt`) and it will create new default ones. These can be then modified freely and preserved in the future. For more info read [here](https://github.com/alemelis/sd-webui-ar/issues/9).

## Install

Browse to the `Extensions` tab -> go to `Install from URL` -> paste in `https://github.com/alemelis/sd-webui-ar` -> click `Install`


Here's how the UI looks like after installing this extension

<img width="666" alt="Screenshot 2023-03-30 at 20 37 56" src="https://user-images.githubusercontent.com/4661737/228946744-dbffc4c6-8a3f-4a42-8e47-1056b3558afc.png">

## Usage

- Click on the aspect ratio button you want to set. In the case of an aspect ratio greater than 1, the script fixes the width and changes the height. Whereas if the aspect ratio is smaller than 1, the width changes while the height is fixed.
- Reset image resolution by clicking on one of the buttons on the second row.

### Configuration

Aspect ratios can be defined in the `/sd-webui-ar/aspect_ratios.txt` file. For example,

```
1:1, 1.0
3:2, 3/2
4:3, 4/3
16:9, 16/9
# 6:13, 6/13
# 9:16, 9/16
# 3:5, 3/5
# 2:3, 2/3
# 19:16, 19/16 # fox movietone
# 5:4, 5/4 # medium format photo
# 11:8, 11/8 # academy standard
# IMAX, 1.43
# 14:9, 14/9
# 16:10, 16/10
# 𝜑, 1.6180 # golden ratio
# 5:3, 5/3 # super 16mm
# 1.85, 1.85 # US widescreen cinema
# DCI, 1.9 # digital imax
# 2:1, 2.0 # univisium
# 70mm, 2.2
# 21:9, 21/9 # cinematic wide screen
# δ, 2.414 # silver ratio
# UPV70, 2.76 # ultra panavision 70
# 32:9, 32/9 # ultra wide screen
# PV, 4.0 # polyvision
```

Note the `#` marking the line as a comment, i.e. the extension is not reading that line. To use a custom value, un-comment the relative line by removing the starting `#`.
A custom aspect ratio is defined as `button-label, aspect-ratio-value # comment`. It is recommended to set the `aspect-ratio-value` to a fraction, but a `float` or `int` will work as well. The `# comment` is optional.
The `button-label` will be displayed inside the button. It can be anything you like.

Resolutions presets are defined inside `resolutions.txt` file,

```
1, 512, 512 # 1:1 square
2, 768, 512 # 3:2 landscape
3, 403, 716 # 9:16 portrait
```

The format to be used is `button-label, width, height, # optional comment`. As before, lines starting with `#` will be ignored.

## Calculator Panel
Use the calculator to determine new width or height values based on the aspect ratio of source dimensions.
- Click `Calc` to show or hide the aspect ratio calculator
- Set the source dimensions:
  - Enter manually, or
  - Click ⬇️ to get source dimentions from txt2img/img2img sliders, or
  - Click 🖼️ to get source dimensions from input image component on the current tab
- Click ⇅ to swap the width and height, if desired
- Set the desired width or height, then click either `Calculate Height` or `Calculate Width` to calculate the missing value
- Click `Apply` to send the values to the txt2txt/img2img sliders
---
<img width="666" style="border: solid 3px black;" alt="Basic usage of aspect ratio calculator" src="https://user-images.githubusercontent.com/121050401/229391634-4ec06027-e603-4672-bad9-ec77647b0941.gif">

</details>
