Configuration file
==================


Introduction
------------

There are four main sections that make up the configuration file: backpop settings, observables, priors, and the COSMIC 
dictionaries (i.e. BSEDict and SSEDict). Below shows each input needed for the INI file with a discription of its use 
and allowed value or string. The default settings are noted in the comments.

COSMIC
~~~~~~

Within COSMIC, there is a modified version of BSE needed to run ``cosmic-pop``. The BSEDict has a number of flags that 
allows the user to tailor the binary evolution. 

For your BackPop run, you will need to set up this dictionary. You can do so by clicking the button below. This page 
allows you to interactively select the flags and will populate the 
`BSEDict <https://cosmic-popsynth.github.io/COSMIC/pages/config_and_output/inifile.html#python-bse-settings-dictionary>`_ 
you can copy at the end.


.. raw:: html

    <div class="toms-nav-container" style="margin-bottom: 3rem; height: 90px; grid-template-rows: 90px">
        <div class="box" data-href="https://cosmic-popsynth.github.io/COSMIC/pages/config_and_output/inifile.html#inifile">COSMIC BSEDict</div>
    </div>

How to use this page
~~~~~~~~~~~~~~~~~~~~

**Reference guide** - this page is a great reference for *every* setting available in BackPop and explains each of the 
options.

**Interactive config generator** - it can also be used interactively to generate your very own configuration file 
for running BackPop. In each of the following sections you can edit the values of the parameter and the files at the 
end of the page will update in turn for you to copy. Enjoy configuring BackPop!

Settings
--------

BackPop
~~~~~~~

.. raw:: html
    :file: ../../_generated/config_insert_BackPop.html

Observables
~~~~~~~~~~~

.. raw:: html
    :file: ../../_generated/config_insert_observables.html

Priors
~~~~~~

.. raw:: html
    :file: ../../_generated/config_insert_priors.html

SSEDict
~~~~~~~

.. raw:: html
    :file: ../../_generated/config_insert_sse.html


INI file
--------

Use the button below to toggle whether to include explanatory comments in the INI file.

.. raw:: html
    <button id="ini-file-comments" type="button" class="btn btn-toggle">Show comments</button>

.. code-block:: ini

    INIFILE HERE

.. raw:: html

    <script src="../../_static/settings.js"></script>