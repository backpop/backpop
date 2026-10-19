"""
    create_settings_html.py

    This file is used to construct the HTML files for the config/settings page
    based on the information stored in backpop-settings.json.

    Written by Tom Wagg
    Edited by Hannah Skobe
"""

import bs4
import json
import os
import pandas as pd
from backpop import __version__ as backpop_version

# how many versions in the past should we show as badges for when options were added?
VERSION_CUTOFFS = {
    "major": 1000,
    "minor": 1000,
    "patch": 1000
}

def version_is_recent(version_string):
    version_nums = version_string.split(".")
    backpop_nums = backpop_version.split(".")
    for i, label in enumerate(["major", "minor", "patch"]):
        if int(backpop_nums[i]) - int(version_nums[i]) > VERSION_CUTOFFS[label]:
            return False
    return True

# blame BS4 for me calling this soup
main_soup = """<!-- This file should be created using create_settings_html.py -->
<div class="container-fluid"></div>
"""

# a template for a settings group (we'll copy this and fill it in)
group_template = """<section class="card setting-card">
        <div class="card-header">
            <h2 class="setting-group-title"></h2>
            <p class="setting-group-description"></p>
        </div>
        <div class="card-body"></div>
    </section>"""

# as above but for a specific setting (this'll go in 'card-body' above)
settings_template = """<div class="setting">
                <div class="row align-items-center setting-chooser">
                    <div class="col-9">
                        <div class='name-cont'><h4 class="name"><code></code></h4><span class="version-added"></span></div>
                        <p class="description"></p>
                        <p class="default"></p>
                    </div>
                    <div class="col-3">
                    </div>
                </div>
                <div class="options-expander">Option details <i class="fa-solid fa-chevron-down"></i></div>
                <div class="row options hide">
                    <p class="options-preface"></p>
                    <ul style="margin-left: 2rem; max-width: calc(100% - 2rem)"></ul>
                </div>
            </div>"""

# same as above, but for an option for a setting, this will go in the <ul> element
option_template = """<li><code class="docutils literal notranslate"><span class="pre opt-val"></span></code>: <span class="opt-desc"></span><span class="opt-badge-cont"></span></li>"""

# categories whose settings-sections get an "include in output" enable/disable toggle
TOGGLEABLE_CATEGORIES = ("observables", "priors")


def build_section_toggle_html(section_id):
    """Build the checkbox toggle that enables/disables an entire settings-section
    (e.g. one observable or one prior). Handled client-side by settings.js.

    Parameters
    ----------
    section_id : `str`
        The slugified id of the settings-section this toggle controls

    Returns
    -------
    html : `str`
        HTML for the toggle switch
    """
    return f"""<div class="form-check form-switch section-toggle">
        <input class="form-check-input section-enable-toggle" type="checkbox" role="switch"
               id="enable-{section_id}" data-section="{section_id}" checked>
        <label class="form-check-label" for="enable-{section_id}" style="font-size: 14px; margin-left: 8px">Add to INI</label>
    </div>"""


def build_add_more_priors_html(setting):
    """Build the "add additional priors" block that goes at the end of the Priors
    category. This lets users add an unlimited number of extra priors (each with
    a name, min and max) that get picked up by settings.js when constructing the
    ini file preview.

    Parameters
    ----------
    setting : `dict`
        The `add-more-priors` sentinel entry from backpop-settings.json

    Returns
    -------
    html : `str`
        HTML for the add-more-priors block
    """
    name_placeholder = setting.get("name-placeholder", "prior name")
    button_label = setting.get("add-button-label", "Additional Prior")

    return f"""<div class="setting custom-priors-block">
        <div id="custom-priors-list" class="custom-priors-list"></div>
        <button type="button" id="add-custom-prior-btn" class="btn btn-outline-primary add-prior-btn" style="margin-top: 30px; background-color: #78B8A0";>{button_label}</button>
        <template id="custom-prior-template">
            <div class="custom-prior-row row align-items-center" style="margin-top: 30px">
                <div class="col-5">
                    <input type="text" class="custom-prior-input custom-prior-name form-control"
                           placeholder="{name_placeholder}">
                </div>
                <div class="col-3">
                    <input type="number" class="custom-prior-input custom-prior-min form-control" placeholder="min">
                </div>
                <div class="col-3">
                    <input type="number" class="custom-prior-input custom-prior-max form-control" placeholder="max">
                </div>
                <div class="col-1">
                    <button type="button" class="btn btn-sm btn-outline-danger remove-custom-prior" style="padding: 0.5rem; background-color: #78B8A0" title="Remove this prior">&times;</button>
                </div>
            </div>
        </template>
    </div>"""

# read the settings file
with open("backpop-settings.json") as f:
    settings = json.load(f)

# go through each major settings group
for group in settings:
    # start the overall main html file
    soup = bs4.BeautifulSoup(main_soup, 'html.parser')

    # start a new group, writing in its category name, label and description
    new_group = bs4.BeautifulSoup(group_template, 'html.parser')
    new_group.section["data-category"] = group["category"]
    title = new_group.select_one(".setting-group-title")
    title.string = group["category_label"]
    new_group.select_one(".setting-group-description").string = group["category_description"]

    # update the colours based on the choices in the JSON file
    new_group.select_one(".setting-card")["style"] = "border-color: " + group["docs-colour"] + ";"
    new_group.select_one(".card-header")["style"] = "background-color: " + group["docs-colour"] + ";"

    # track which settings-section (e.g. "Primary Mass") we're currently inside, so
    # that we can tag each setting with it (used for the observable/prior enable toggle)
    current_section_id = None

    # proceed through the settings in this group
    for setting in group["settings"]:
        # if this is the start of a subsection (e.g. "Mass transfer")
        if "settings-section" in setting:
            current_section_id = setting["settings-section"].lower().replace(" ", "-")

            # create a section and add a heading with the title
            settings_section = new_group.new_tag("div")
            settings_section["class"] = "settings-section"
            settings_section["data-section"] = current_section_id

            header_row = new_group.new_tag("div")
            header_row["class"] = "settings-section-header d-flex justify-content-between align-items-center"

            header = new_group.new_tag("h3")
            header["id"] = current_section_id
            header.string = setting["settings-section"]
            header_row.append(header)

            # observables and priors each get a toggle to include/exclude them from the
            # output ini file (the "add more priors" sentinel gets its own UI instead)
            if group["category"] in TOGGLEABLE_CATEGORIES and not setting.get("add-more-priors"):
                header_row.append(bs4.BeautifulSoup(build_section_toggle_html(current_section_id),
                                                    'html.parser'))

            settings_section.append(header_row)
            hr_tag = settings_section.append(new_group.new_tag("hr"))
            hr_tag['style'] = "background-color: #dabfcd7c; height: 2px; border: none;"
            settings_section.append(hr_tag)


            # add an optional description if it's there (e.g. Common-envelope has this)
            if "settings-section-description" in setting:
                settings_section_description = new_group.new_tag("p")
                settings_section_description.string = setting["settings-section-description"]
                settings_section.append(settings_section_description)

            new_group.select_one(".card-body").append(settings_section)

        # the "add more priors" sentinel isn't a real setting - swap in the custom
        # priors UI instead and skip the regular setting-building logic below
        if setting.get("add-more-priors"):
            new_group.select_one(".card-body").append(
                bs4.BeautifulSoup(build_add_more_priors_html(setting), 'html.parser'))
            continue

        # create the new settings with its details
        new_setting = bs4.BeautifulSoup(settings_template, 'html.parser')
        new_setting.select_one(".name").code.string = setting["name"]
        new_setting.select_one(".description").clear()
        new_setting.select_one(".description").append(bs4.BeautifulSoup(setting["description"],
                                                                        'html.parser'))
        
        # add the version added if it's there
        if "version_added" in setting:
            if version_is_recent(setting["version_added"]):
                new_setting.select_one(".version-added").append(bs4.BeautifulSoup(
                    f"""<span class="badge badge-success version-added"><a class="link-white" href="https://github.com/backpop/backpop/tags/v{setting['version_added']}">Added in v{setting['version_added']}</a></span>""", 'html.parser'))

        # colour the sublinks the same as the border of the group
        new_setting.select_one(".options-expander")["style"] = "color: " + group["docs-colour"] + ";"

        # track the default value
        default = []

        if setting["type"] == "checkbox":
            insert_here = new_setting.select_one(".col-3")
            for i, option in enumerate(setting["options"]):
                # append to the default as necessary
                if "default" not in option:
                    option["default"] = False
                elif option["default"]:
                    default.append(option["name"])

                # create a checkbox with the option details
                new_option = new_setting.new_tag("input", type="checkbox", value=option["name"])
                if option["default"]:
                    new_option["checked"] = "true"
                new_option["name"] = f"{setting['name']}_opt{i}"
                new_label = new_setting.new_tag("label", for_=f"{setting['name']}_opt{i}")
                new_label.string = f" {option['name']}"

                new_container = new_setting.new_tag("div")
                new_container.append(new_option)
                new_container.append(new_label)

                insert_here.append(new_container)

            # create a secret hidden input which combines the checkbox inputs
            secret_input = new_setting.new_tag("input", type="string", value="")
            secret_input["class"] = "form-control hide-me"
            secret_input["value"] = str(default).replace("'", "")
            insert_here.append(secret_input)

        elif setting["type"] in ["string", "number"]:
            for option in setting["options"]:
                # create an input with the value of the default option
                if "default" in option and option["default"]:
                    default = option["name"]
                    new_option = new_setting.new_tag("input",
                                                     type="text" if setting["type"] == "string" else "number",
                                                     value=str(option["name"]))
                    new_option["class"] = "form-control"
                    new_setting.select_one(".col-3").append(new_option)
                    break

        elif setting["type"] == "dropdown":
            # create a dropdown input with all of the potential options
            new_select = new_setting.new_tag("select")
            new_select["class"] = "form-control"

            # special-cased dropdown (currently just the metallicity fixed/variable
            # toggle) - tag it with an id so settings.js can wire up a listener that
            # shows/hides the fields that go with whichever mode is selected
            if setting.get("is-metallicity-mode-toggle"):
                new_select["id"] = "metallicity-mode-toggle"

            for i, option in enumerate(setting["options"]):
                new_option = new_setting.new_tag("option", value=option["name"])
                new_option.string = str(option["name"])
                if "default" in option and option["default"]:
                    new_option["selected"] = "true"
                    default = option["name"]
                new_select.append(new_option)
            new_setting.select_one(".col-3").append(new_select)

        # optionally there might be some extra explanation about the options
        if setting["options-preface"] != "":
            new_setting.select_one(".options-preface").clear()
            new_setting.select_one(".options-preface").append(bs4.BeautifulSoup(setting["options-preface"],
                                                                                'html.parser'))

        # add each of the options and its explanation to the list
        for i, option in enumerate(setting["options"]):
            new_option_expl = bs4.BeautifulSoup(option_template, 'html.parser')
            new_option_expl.select_one(".opt-val").string = str(option["name"])
            new_option_expl.select_one(".opt-desc").append(bs4.BeautifulSoup(option["description"], 'html.parser'))

            if "version_added" in option:
                if version_is_recent(option["version_added"]):
                    new_option_expl.select_one(".opt-badge-cont").append(bs4.BeautifulSoup(
                        f"""<span class="badge badge-success version-added"><a class="link-white" href="https://github.com/backpop/backpop/tags/v{option['version_added']}">Added in v{option['version_added']}</a></span>""", 'html.parser'
                    ))
            new_setting.select_one(".options").ul.append(new_option_expl)

        # convert the default options to a string and display it
        default_string = str(default)
        default_string = default_string.replace("'", "")
        new_setting.select_one(".default").string = f"Default: {default_string}"

        # tag this setting with its enclosing section so settings.js can gray it out
        # and exclude it from the ini file when the section's toggle is switched off
        if group["category"] in TOGGLEABLE_CATEGORIES and current_section_id is not None:
            new_setting.select_one(".setting")["data-section"] = current_section_id

        # tag fields that only apply in one metallicity mode (fixed vs. variable) so
        # settings.js can show/hide the right ones based on the mode toggle above
        if "metallicity-field" in setting:
            new_setting.select_one(".setting")["data-metallicity-field"] = setting["metallicity-field"]

        # append this setting to the group
        new_group.select_one(".card-body").append(new_setting)

    # append this group to the soup (guess who's a poet and didn't even know it)
    soup.select_one(".container-fluid").append(new_group)

    # write the soup out to an HTML file for this category
    os.makedirs("_generated", exist_ok=True)
    with open(f"_generated/config_insert_{group['category']}.html", "w") as f:
        f.write(str(soup))
