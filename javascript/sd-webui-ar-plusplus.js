if ("undefined" === typeof arsp__ar_button_titles) {
	arsp__ar_button_titles = {};
}

arsp__ar_button_titles[" \u{1F513}"] = 'Toggle to lock the "average" width/height values in the UI\nIt is recommended to "Lock" when switching between ARs in "Offset" mode.\n\n\u{1F512} = Locked\n\u{1F513} = Unlocked';
arsp__ar_button_titles[" \u{025AD}"] = 'For "Offset mode" (default):\n\u{025AF} = Portrait resolutions\n\u{025AD} = Landscape resolutions\n\nFor "One Dimension" mode:\n\u{025AD} = Modify Width\n\u{025AF} = Modify Height';
arsp__ar_button_titles[" \u{02B83}"] = 'Toggle the Mode for updating resolution.\nResolution is always rounded to precision (default 64px).\n\n\u{02B83} = "Offset" updates both Width/Height from the average current resolution\n\u{02B85} = "One Dimension" changes only Width or Height';
arsp__ar_button_titles[" \u{02139}"] = 'Show the Information panel including additional settings.'
arsp__ar_button_titles[" \u{02BC5}"] = 'Hide the Information panel.'

onUiUpdate(function(){
	gradioApp().querySelectorAll('#arsp__txt2img_container_aspect_ratio button, #arsp__img2img_container_aspect_ratio button').forEach(function(elem){
		tooltip = arsp__ar_button_titles[elem.textContent];
		if(tooltip){
		 	elem.title = tooltip;
		}
	})
})