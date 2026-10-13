import argparse
import json
import re

# regular expression for html tags
html_tag = r"<[^>]*>"

# convertor for html tags to ini file decorators
replacer = {
    "code": "``",
    "b": "**",
    "i": "*"
}


def replace_tag(m):
    """Replace HTML tags with some decoration in the ini file

    Parameters
    ----------
    m : `re.Match`
        A match from a regular expression (containing an HTML tag)

    Returns
    -------
    r : `str`
        Replacement string
    """
    # grab the tag out of the regular expression match
    match = m.group()
    full_tag = match.replace("/", "").replace("<", "").replace(">", "")
    tag = full_tag.split(" ")[0]

    # by default delete the tag, but replace if it's in the dictionary
    replacement = ""
    if tag in replacer:
        replacement = replacer[tag]

    return replacement


# 'settings' becomes a single flat [backpop] section in the ini file;
# 'observables'/'priors'/'sse' keep their category name as-is
CATEGORY_INI_NAME = {
    "settings": "backpop",
}

# comment printed above each of these categories instead of a literal
# bracketed header, since 'observables' and 'priors' don't get a single
# [observables]/[priors] section - they're split into one bracketed
# section per settings-section (see get_section_code below)
CATEGORY_COMMENT = {
    "settings": "; Main backpop settings",
    "observables": "; Observational constraints",
    "priors": "; Prior info on parameters to vary",
}

# maps a settings-section title to BackPop/COSMIC's short internal
# parameter code used in the ini section header, e.g. [backpop.obs::m1].
# NOTE: this is intentionally NOT the same as a setting's "out_name" value
# (out_name is the COSMIC BPP/BCM output column to compare against, e.g.
# "mass_1" - a different concept from the short code "m1" used here)
SECTION_CODE = {
    "Primary Mass": "m1",
    "Secondary Mass": "m2",
    "Orbital Period": "tb",
    "Eccentricity": "e",
    "Metallicity": "metallicity",
    "Evolution Time": "tphys",
}


def get_section_code(section_title):
    """Map a settings-section title to its short backpop parameter code.

    Falls back to a slugified version of the title for any section not in
    the SECTION_CODE lookup above (e.g. a custom prior added at runtime via
    the "add more priors" feature, whose title IS its own short code).

    Parameters
    ----------
    section_title : `str`
        The "settings-section" title, e.g. "Primary Mass" or "Primary Mass Prior"

    Returns
    -------
    code : `str`
        The short code to use in the ini section header, e.g. "m1"
    """
    # priors are titled e.g. "Primary Mass Prior" - strip that suffix before
    # looking the title up so a prior lands on the same code as its matching
    # observable (both become "m1"), rather than falling through to a
    # slugified "primary_mass_prior"
    base_title = section_title[: -len(" Prior")] if section_title.endswith(" Prior") else section_title
    return SECTION_CODE.get(base_title, base_title.lower().replace(" ", "_"))


def group_settings_by_section(settings_list):
    """Split a flat settings list into (section_title, [settings]) chunks.

    Parameters
    ----------
    settings_list : `list`
        A category's flat "settings" list, where a "settings-section" key
        marks the first setting of a new subsection (see backpop-settings.json)

    Returns
    -------
    groups : `list`
        List of (section_title, [settings]) tuples. section_title is None
        for any settings that appear before the first section marker (e.g.
        a flat, non-subsectioned category like 'settings' or 'sse')
    """
    groups = []
    current_title = None
    current_settings = []
    for setting in settings_list:
        if "settings-section" in setting:
            if current_settings:
                groups.append((current_title, current_settings))
            current_title = setting["settings-section"]
            current_settings = []
        current_settings.append(setting)
    if current_settings:
        groups.append((current_title, current_settings))
    return groups


def get_metallicity_mode(group_settings):
    """Work out whether a "Metallicity" settings-section is fixed or variable.

    Looks for the "metallicity_mode" toggle setting within the section and
    returns whichever of its options is marked as the default (falling back
    to "fixed" if the toggle can't be found).

    Parameters
    ----------
    group_settings : `list`
        The settings that make up the "Metallicity" settings-section

    Returns
    -------
    mode : `str`
        Either ``"fixed"`` or ``"variable"``
    """
    for setting in group_settings:
        if setting.get("is-metallicity-mode-toggle"):
            for option in setting["options"]:
                if option.get("default"):
                    return option["name"]
    return "fixed"


def render_setting(setting, include_comments):
    """Render a single setting as its INI comment block plus key/value line

    Parameters
    ----------
    setting : `dict`
        A single setting dictionary from backpop-settings.json
    include_comments : `bool`
        Whether to include the descriptive comment block above the setting

    Returns
    -------
    line : `str`
        The rendered comment block (if requested) and `name = default` line
    """
    comments = ""
    if "settings-section-description" in setting:
        comments += f'; {setting["settings-section-description"]}\n'

    comments += f'\n; {setting["name"]}\n'
    comments += f'; {setting["description"]}\n'
    if "options-preface" in setting:
        comments += f'; {setting["options-preface"]}\n'

    comments += "; Options: \n"

    default = []
    for option in setting["options"]:
        comments += f';    {option["name"]} - {option["description"]}\n'

        if "default" in option and option["default"]:
            if setting["type"] == "checkbox":
                default.append(str(option["name"]))
            elif option["name"] == "":
                default = '""'
            else:
                default = str(option["name"])

    default_string = f"[{', '.join(default)}]" if isinstance(default, list) else f"{default}"
    comments += f"; Default: {default_string}\n"

    line = comments if include_comments else ""
    line += f'{setting["name"]} = {default_string}\n'
    return line


def render_priors_section(section_title, group_settings, include_comments):
    """Render one [backpop.var::...] priors section

    Parameters
    ----------
    section_title : `str`
        The settings-section title, e.g. "Primary Mass Prior"
    group_settings : `list`
        The settings that make up this section (e.g. min/max)
    include_comments : `bool`
        Whether to include the descriptive comment block above each setting

    Returns
    -------
    ini_file : `str`
        The rendered `[backpop.var::...]` section
    """
    code = get_section_code(section_title)
    ini_file = f"\n[backpop.var::{code}]\n"
    for setting in group_settings:
        ini_file += render_setting(setting, include_comments)
    return ini_file


def render_extra_priors(extra_priors, include_comments):
    """Render additional user-added priors (from the Configuration page's
    "Additional Priors" section) as their own [backpop.var::<name>] sections,
    matching how settings.js renders them in the live ini file preview.

    Parameters
    ----------
    extra_priors : `list`
        List of dicts, each with ``name``, ``min`` and ``max`` keys - mirrors
        the custom-prior rows a user can add on the Configuration page
    include_comments : `bool`
        Whether to include a comment above each additional prior

    Returns
    -------
    ini_file : `str`
        The rendered additional `[backpop.var::...]` sections
    """
    ini_file = ""
    for prior in extra_priors:
        name = str(prior["name"]).strip()
        if not name:
            continue
        code = name.lower().replace(" ", "_")
        ini_file += f"\n[backpop.var::{code}]\n"
        if include_comments:
            ini_file += "; User-added prior\n"
        ini_file += f'min = {prior["min"]}\n'
        ini_file += f'max = {prior["max"]}\n'
    return ini_file


def construct_ini_from_json(config, include_comments=True, extra_priors=None):
    """Construct an INI file from the JSON

    'settings' is rendered as a single flat [backpop] section. 'observables'
    and 'priors' are split into one bracketed section per settings-section
    (e.g. [backpop.obs::m1], [backpop.fixed::metallicity], [backpop.var::m1])
    rather than a single [observables]/[priors] section, matching the
    framework used in VFTS243.ini. 'sse' (and any other category) keeps the
    original flat rendering with decorative ";;;;" subheadings.

    Metallicity is special-cased: its settings-section holds a
    "metallicity_mode" toggle plus both a fixed "value" field and a
    variable "mean"/"sigma"/"out_name" set of fields, and only the fields
    matching the toggle's default ("fixed" unless the JSON says otherwise)
    are rendered, as either `[backpop.fixed::metallicity]` (fixed) or
    `[backpop.obs::metallicity]` (variable).

    Parameters
    ----------
    config : `dict`
        Dictionary built from the JSON file
    include_comments : `bool`, optional
        Whether to include comments in the INI file, by default True
    extra_priors : `list`, optional
        Additional user-added priors (e.g. from the Configuration page's
        "Additional Priors" section), each a dict with ``name``, ``min`` and
        ``max`` keys. These are appended after the built-in `[priors]`
        entries as their own `[backpop.var::<name>]` sections, by default None

    Returns
    -------
    ini_file : `str`
        INI file for writing to a file
    """
    ini_file = "; BackPop INI file\n"

    for category in config:
        cat_name = category["category"]

        # drop any placeholder settings (e.g. the "add more priors" UI
        # trigger in the JSON) - these aren't real settings to render
        settings_list = [s for s in category["settings"] if not s.get("add-more-priors")]

        if cat_name in CATEGORY_COMMENT:
            ini_file += f"\n{CATEGORY_COMMENT[cat_name]}\n"
            groups = group_settings_by_section(settings_list)

            if cat_name == "settings":
                # single flat section, renamed to [backpop]
                ini_file += f"[{CATEGORY_INI_NAME[cat_name]}]\n"
                for _, group_settings in groups:
                    for setting in group_settings:
                        ini_file += render_setting(setting, include_comments)
            elif cat_name == "priors":
                # priors: one bracketed ini section per settings-section,
                # e.g. [backpop.var::m1], plus any additional user-added priors
                for section_title, group_settings in groups:
                    if section_title is None:
                        ini_file += "\n[backpop.var]\n"
                        for setting in group_settings:
                            ini_file += render_setting(setting, include_comments)
                    else:
                        ini_file += render_priors_section(section_title, group_settings, include_comments)

                if extra_priors:
                    ini_file += render_extra_priors(extra_priors, include_comments)
            else:
                # observables: one bracketed ini section per settings-section,
                # e.g. [backpop.obs::m1], [backpop.fixed::metallicity]
                for section_title, group_settings in groups:
                    if section_title is None:
                        # shouldn't normally happen here, but guard against a
                        # stray setting with no section marker
                        ini_file += "\n[backpop.obs]\n"
                        for setting in group_settings:
                            ini_file += render_setting(setting, include_comments)
                        continue

                    code = get_section_code(section_title)

                    if section_title == "Metallicity":
                        # metallicity can be fixed (a single "value") or
                        # variable (mean/sigma/out_name, like the other
                        # observables) - render only the active mode's fields
                        mode = get_metallicity_mode(group_settings)
                        prefix = "obs" if mode == "variable" else "fixed"
                        active_settings = [s for s in group_settings
                                          if not s.get("is-metallicity-mode-toggle")
                                          and s.get("metallicity-field", mode) == mode]
                        ini_file += f"\n[backpop.{prefix}::{code}]\n"
                        for setting in active_settings:
                            ini_file += render_setting(setting, include_comments)
                        continue

                    # sections with an "out_name" setting are real
                    # observational constraints ([backpop.obs::...]);
                    # single-setting "value" sections (e.g. Evolution Time)
                    # are fixed inputs ([backpop.fixed::...])
                    is_obs = any(s["name"] == "out_name" for s in group_settings)
                    prefix = "obs" if is_obs else "fixed"

                    ini_file += f"\n[backpop.{prefix}::{code}]\n"
                    for setting in group_settings:
                        ini_file += render_setting(setting, include_comments)
        else:
            # unchanged behaviour for any other category (e.g. 'sse') -
            # keep the original flat rendering with decorative subheadings
            ini_file += f"\n[{cat_name}]\n"
            for setting in settings_list:
                if "settings-section" in setting:
                    subheading = setting["settings-section"]
                    ini_file += '\n;;;;' + ';' * len(subheading) + ';;;;\n'
                    ini_file += f';;; {subheading} ;;;'
                    ini_file += '\n;;;;' + ';' * len(subheading) + ';;;;\n'
                ini_file += render_setting(setting, include_comments)

    return ini_file


def main():
    parser = argparse.ArgumentParser(
        description="Build a BackPop INI file from backpop-settings.json, "
                     "in the same layout as VFTS243.ini")
    parser.add_argument("--no-comments", action="store_true",
                        help="Omit the descriptive comment blocks above each setting")
    parser.add_argument("--extra-priors", type=str, default=None,
                        help="Path to a JSON file containing a list of additional "
                             "user-added priors (each a dict with 'name', 'min' and "
                             "'max' keys), e.g. as added via the 'Additional Priors' "
                             "section of the Configuration page")
    parser.add_argument("--output", type=str, default="../params.ini",
                        help="Where to write the generated INI file")
    args = parser.parse_args()

    # read the config file
    with open("backpop-settings.json") as f:
        config = json.load(f)

    extra_priors = None
    if args.extra_priors is not None:
        with open(args.extra_priors) as f:
            extra_priors = json.load(f)

    # convert it to an INI file, replace HTML tags and save the output
    with open(args.output, "w") as f:
        f.write(re.sub(pattern=html_tag,
                       repl=replace_tag,
                       string=construct_ini_from_json(config,
                                                       include_comments=not args.no_comments,
                                                       extra_priors=extra_priors)))


if __name__ == "__main__":
    main()