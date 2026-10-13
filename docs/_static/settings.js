/* 
    settings.js

    This file gets injected into the config/settings page and handles
    the various interactive aspects of the page

    written by Tom Wagg
    edited by Hannah Skobe

*/

// once the page loads, run this function
document.addEventListener("DOMContentLoaded", function() {
    // hide the dummy maths element
    document.getElementById("hide-this-maths").classList.add("hide-me");

    // show/hide options any time the expander is clicked (and switch up/down arrow)
    document.querySelectorAll(".options-expander").forEach(expander => {
        expander.addEventListener("click", function() {
            expander.parentElement.querySelector(".options").classList.toggle("hide");
            const icon = expander.querySelector("i");
            if (icon) {
                icon.classList.toggle("fa-chevron-down");
                icon.classList.toggle("fa-chevron-up");
            }
        });
    });

    // make it so that checkbox labels can also be clicked instead of just the tiny box
    document.querySelectorAll(".col-3 label").forEach(label => {
        label.addEventListener("click", function() {
            label.parentElement.querySelector("input").click();
        });
    });

    // hide the dummy headings that are just for the toc (please don't judge my hack haha)
    document.querySelectorAll("h3:not(.setting-group-title)").forEach(h3 => {
        let my_headings = document.querySelectorAll("h2.setting-group-title");
        for (let heading of my_headings) {
            if (heading.innerText == h3.innerText) {
                h3.style = "height: 0; margin: 0; overflow: hidden;";
                break;
            }
        }
    });

    // hack the TOC on the right to include the subheadings from ANY category that uses .settings-section subcategories
    const lis = document.querySelectorAll(".toc-drawer li");
    for (let li of lis) {
        const matching_cards = document.querySelectorAll(".card.setting-card");
        let matching_card = null;
        for (let card of matching_cards) {
            const header = card.querySelector(".setting-group-title");
            if (header && header.innerText.trim().toLowerCase() == li.innerText.trim().toLowerCase()) {
                matching_card = card;
                break;
            }
        }
        if (!matching_card) continue;

        // only that card's own subsections (not every subsection on the page)
        // NOTE: matches h3 too
        const subheadings = matching_card.querySelectorAll(".settings-section h2, .settings-section h3");
        if (subheadings.length == 0) continue;

        const new_ul = document.createElement("ul");
        for (let subheading of subheadings) {
            const new_li = document.createElement("li");
            new_li.innerHTML = `<a class="reference internal" href="#${subheading.id}">${subheading.innerText}</a>`;
            new_ul.appendChild(new_li);
        }
        li.appendChild(new_ul);
    }

    // update hidden inputs based on the checkbox choices anytime one of them in a group is clicked
    document.querySelectorAll("input[type='checkbox']").forEach(checkbox => {
        checkbox.addEventListener("change", function() {
            const checked = checkbox.parentElement.parentElement.querySelectorAll("input[type='checkbox']");
            value = "[]";
            if (checked.length > 0) {
                value = "[";
                for (let check of checked) {
                    if (check.checked) {
                        value += `${check.value}, `;
                    }
                }
                value = value == "[" ? "[]" : value.slice(0, -2) + "]";
            }
            checkbox.parentElement.parentElement.querySelector("input.hide-me").value = value;
        });
    });

    // wire up the metallicity fixed/variable toggle FIRST, so that when it fires
    // it has already shown/hidden (and enabled/disabled) the right fields before
    // the generic ".form-control" listener below re-builds the ini file preview
    const metallicity_toggle = document.getElementById("metallicity-mode-toggle");
    if (metallicity_toggle) {
        metallicity_toggle.addEventListener("change", apply_metallicity_mode);
    }

    // reconstruct the interactive files any time any input changes
    document.querySelectorAll(".form-control").forEach(input => {
        input.addEventListener("change", function() {
            construct_files()
        });
    });

    // wire up the "include in output" toggle for each observable/prior section:
    // flipping it off disables (and grays out) all inputs in that section and
    // drops them from the generated ini file, flipping it back on restores them
    document.querySelectorAll(".section-enable-toggle").forEach(toggle => {
        toggle.addEventListener("change", function() {
            const section = toggle.dataset.section;
            document.querySelectorAll(`.setting[data-section="${section}"]`).forEach(settingEl => {
                settingEl.classList.toggle("section-disabled", !toggle.checked);
                settingEl.querySelectorAll("input, select").forEach(input => {
                    input.disabled = !toggle.checked;
                });
            });
            construct_files();
        });
    });

    // wire up the "add more priors" affordance at the end of the Priors category,
    // letting users append an unlimited number of custom priors (name + min + max)
    setup_custom_priors();

    // setup the toggle button for including comments in the ini file
    document.getElementById("ini-file-comments").addEventListener("click", function() {
        this.classList.toggle("active");
        this.innerText = this.classList.contains("active") ? "Hide Comments" : "Show Comments";
        construct_files();
    });

    // make sure only the fixed- or variable-mode metallicity fields are active
    // before the very first ini file is built
    apply_metallicity_mode();

    // construct the files once everything is loaded in
    construct_files();
});


// Metallicity in Observables can be set up as either a single fixed value or as
// a variable observable (mean/sigma/out_name, like mass/period/eccentricity).
// This shows/enables whichever set of fields matches the toggle's current value
// and hides/disables (so it's skipped when building the ini file) the other set.
function apply_metallicity_mode() {
    const toggle = document.getElementById("metallicity-mode-toggle");
    if (!toggle) return;

    const mode = toggle.value; // "fixed" or "variable"
    document.querySelectorAll("[data-metallicity-field]").forEach(settingEl => {
        const active = settingEl.dataset.metallicityField === mode;
        settingEl.classList.toggle("section-disabled", !active);
        settingEl.querySelectorAll("input, select").forEach(input => {
            input.disabled = !active;
        });
    });
}


function setup_custom_priors() {
    const addBtn = document.getElementById("add-custom-prior-btn");
    const template = document.getElementById("custom-prior-template");
    const list = document.getElementById("custom-priors-list");
    if (!addBtn || !template || !list) return;

    addBtn.addEventListener("click", function() {
        const row = template.content.firstElementChild.cloneNode(true);

        // any edit to the name/min/max should refresh the ini preview
        row.querySelectorAll(".custom-prior-input").forEach(input => {
            input.addEventListener("input", construct_files);
        });

        // let the user remove a prior they added by mistake
        row.querySelector(".remove-custom-prior").addEventListener("click", function() {
            row.remove();
            construct_files();
        });

        list.appendChild(row);
        row.querySelector(".custom-prior-name").focus();
        construct_files();
    });
}

// maps a settings-section title to BackPop/COSMIC's short internal parameter
// code used in the ini section header, e.g. [backpop.obs::m1]. Mirrors
// SECTION_CODE in create_params_ini.py so the live preview here always
// matches what that script would generate from the same choices.
const SECTION_CODE = {
    "Primary Mass": "m1",
    "Secondary Mass": "m2",
    "Orbital Period": "tb",
    "Eccentricity": "e",
    "Metallicity": "metallicity",
    "Evolution Time": "tphys",
};

// 'settings' is rendered as a single flat [backpop] section (renamed from
// its JSON category name) rather than literally "[settings]"
const CATEGORY_INI_NAME = { "settings": "backpop" };

function section_code(title) {
    // priors sections are titled e.g. "Primary Mass Prior" - strip that
    // suffix before looking the title up so they match their observable
    // counterpart's code (both end up as "m1")
    let base_title = title.endsWith(" Prior") ? title.slice(0, -" Prior".length) : title;
    if (SECTION_CODE.hasOwnProperty(base_title)) return SECTION_CODE[base_title];
    return base_title.toLowerCase().replaceAll(" ", "_");
}

// render one form control's comment block (if requested) plus its
// "name = value" ini line
function render_setting_line(el, include_comments) {
    const full_setting = el.closest(".setting");
    if (!full_setting) return "";

    let line = "";
    if (include_comments) {
        line += `<span class="c1">\n; ${full_setting.querySelector(".name").innerText}\n</span>`;

        const description = full_setting.querySelector(".description").innerText.replaceAll('\n', '');
        line += `<span class="c1">; ${description}\n</span>`;

        const options_preface = full_setting.querySelector(".options-preface");
        if (options_preface && options_preface.innerText != "") {
            line += `<span class='c1'>; ${options_preface.innerText.replaceAll('\n', '')}\n</span>`;
        }

        const options = full_setting.querySelectorAll("li");
        if (options.length > 0) {
            line += "<span class='c1'>; Options: \n";
            for (let option of options) {
                line += `<span class='c1'>;    ${option.innerText.replaceAll('\n', '')}\n`;
            }
            line += "</span>";
        }

        const default_value = full_setting.querySelector(".default").innerText;
        line += `<span class="c1">; ${default_value}\n</span>`;
    }

    const label = full_setting.querySelector(".name").innerText;
    const value = el.value;
    line += `<span class="na">${label}</span><span class="na"> = </span><span class="s">${value}\n</span>`;
    return line;
}

// is this .setting (or its enclosing section) currently switched off, either
// via its section's "Add to INI" toggle or (for metallicity) the fixed/variable
// mode toggle? if so it should be left out of the generated ini file entirely
function setting_is_active(el) {
    if (el.disabled) return false;

    const full_setting = el.closest(".setting");
    const sectionId = full_setting ? full_setting.dataset.section : null;
    if (sectionId) {
        const toggle = document.querySelector(`.section-enable-toggle[data-section="${sectionId}"]`);
        if (toggle && !toggle.checked) return false;
    }
    return true;
}

function construct_files() {
    // construct the strings for the INI file
    // the span tags are to match the syntax highlighting for pygments
    let ini_file = "<span class='c1'>; BackPop INI file\n</span>"

    // whether the user wanted to include comments
    const include_comments = document.getElementById("ini-file-comments").classList.contains("active");

    // NOTE: create_settings_html.py does NOT nest each .setting div inside its
    // .settings-section - they're siblings in document order (the
    // .settings-section element is really just the subsection heading/toggle).
    // So we walk the page in flat document order, same as the original
    // implementation, but buffer up each chunk's lines so we can wrap them in
    // the right VFTS243-style bracket header (e.g. [backpop.obs::m1]) once we
    // know whether that chunk turned out to have anything in it.
    let current_category = null;       // "settings" | "sse" | "observables" | "priors"
    let current_section_title = null;  // e.g. "Primary Mass", or null for a flat category
    let section_lines = "";            // ini lines buffered for the chunk currently being built
    let section_has_out_name = false;  // did an active out_name field turn up in this chunk?
    let section_included = true;       // false if this chunk's "Add to INI" toggle is switched off

    // emit whatever's buffered for the current chunk (category or settings-section)
    // under its bracket header, then reset the buffer for the next chunk
    function flush() {
        if (!section_included || section_lines === "") {
            section_lines = "";
            return;
        }

        let header;
        if (current_section_title === null) {
            // flat category chunk: "settings" -> [backpop], "sse" -> [sse]
            const bracket = CATEGORY_INI_NAME.hasOwnProperty(current_category) ? CATEGORY_INI_NAME[current_category] : current_category;
            header = bracket;
        } else {
            const code = section_code(current_section_title);
            let prefix = "var";
            if (current_category === "observables") {
                prefix = section_has_out_name ? "obs" : "fixed";
            }
            header = `backpop.${prefix}::${code}`;
        }

        ini_file += `<span class='k'>\n[${header}]\n</span>` + section_lines;
        section_lines = "";
    }

    document.querySelectorAll(".setting-card, .settings-section, .form-control").forEach(el => {
        if (el.classList.contains("setting-card")) {
            flush();
            current_category = el.getAttribute("data-category");
            current_section_title = null;
            section_has_out_name = false;
            section_included = true;
        } else if (el.classList.contains("settings-section")) {
            flush();
            const sectionId = el.dataset.section;
            const heading = el.querySelector("h2, h3");
            current_section_title = heading ? heading.innerText : null;
            section_has_out_name = false;

            const toggle = document.querySelector(`.section-enable-toggle[data-section="${sectionId}"]`);
            section_included = !(toggle && !toggle.checked);

            // the "Additional Priors" pseudo-section holds no fields of its own -
            // it just houses the user-added custom-prior rows, each of which gets
            // its own [backpop.var::<name>] section, written straight to ini_file
            // (bypassing the buffer, since each row is its own bracket header)
            if (sectionId === "additional-priors") {
                document.querySelectorAll(".custom-prior-row").forEach(row => {
                    const name = row.querySelector(".custom-prior-name").value.trim();
                    if (!name) return; // skip rows the user hasn't named yet

                    const minVal = row.querySelector(".custom-prior-min").value;
                    const maxVal = row.querySelector(".custom-prior-max").value;
                    const code = name.toLowerCase().replaceAll(" ", "_");

                    ini_file += `<span class="k">\n[backpop.var::${code}]\n</span>`;
                    if (include_comments) {
                        ini_file += `<span class="c1">; User-added prior\n</span>`;
                    }
                    ini_file += `<span class="na">min</span><span class="na"> = </span><span class="s">${minVal}\n</span>`;
                    ini_file += `<span class="na">max</span><span class="na"> = </span><span class="s">${maxVal}\n</span>`;
                });
                section_included = false; // nothing left to flush for this pseudo-section
            }
        } else if (el.classList.contains("form-control")) {
            // custom priors are handled above, right when we hit the "Additional
            // Priors" settings-section marker - skip them here
            if (el.classList.contains("custom-prior-input")) return;

            // the metallicity fixed/variable toggle itself is never written into
            // the ini file - only whichever value/mean/sigma/out_name fields it
            // switches on
            if (el.id === "metallicity-mode-toggle") return;

            if (!setting_is_active(el)) return;

            const full_setting = el.closest(".setting");
            const label = full_setting.querySelector(".name").innerText;
            if (label === "out_name") section_has_out_name = true;

            section_lines += render_setting_line(el, include_comments);
        }
    });
    flush(); // flush the final chunk

    // update the actual values on the page with the constructed strings
    //
    // NOTE: this used to select "#ini-file .highlight-ini pre", but
    // "ini-file" is the id Sphinx auto-assigns to the "INI file" <h2>
    // heading above (for the TOC anchor), and the code block is a sibling
    // of that heading rather than a child of it, so that selector always
    // matched nothing. The code block is now wrapped in its own
    // "#ini-file-output" container (see config.rst) so it can actually be
    // found and updated here.
    const ini_pre = document.querySelector("#ini-file-output .highlight-ini pre");
    if (ini_pre) {
        ini_pre.innerHTML = ini_file;
    }
}