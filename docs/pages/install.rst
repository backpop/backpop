Installation
============

Step 1: Create a new environment
--------------------------------

This is optional, but we recommend that you create a new conda environment to install BackPop and its dependencies. You can do this by running the following command in your terminal:

.. code-block:: bash

    conda create -n backpop python=3.11
    conda activate backpop

Step 2: Install ``COSMIC``
--------------------------

First, you'll need the ``COSMIC`` population synthesis code, follow these instructions:

.. note::
    You don't need to create a separate environment for COSMIC, it should be installed in the environment as we just created for ``BackPop`` above.

.. raw:: html

     <iframe id="COSMIC-frame" src="https://cosmic-popsynth.github.io/COSMIC/pages/install.html" title="COSMIC install docs" ></iframe> 


Step 3: Install ``BackPop``!
----------------------------

Now, ensuring you've got your environment activated (see above), you can install BackPop using pip. Run the following command in your terminal:

.. code-block:: bash

    pip install backpop



And that's it! To confirm that everything has installed correctly you can run the following command to print out the version of ``BackPop`` you have installed:

.. code-block:: bash

    python -c "import backpop; print(backpop.__version__)"

If you see the version number printed out without any errors, then you're all set to start using ``BackPop``! For more information on getting started, check out the :ref:`getting_started` page.

Optional: Installing from source with GitHub
--------------------------------------------

If you wish to install BackPop from source, you can clone the repository from GitHub and install it locally using pip. If you decide to go this route, we recommend `creating your own fork <https://github.com/backpop/backpop/fork>`_ of the repository to keep your development work separate from the main repository.

Once you have your own fork, you can clone it as:

.. code-block:: bash

    git clone /link/to/your/forked/repo

Once cloned, navigate to the BackPop directory and install it using pip:

.. code-block:: bash

    cd backpop
    pip install .