Home
====

.. Hell world

.. raw:: html

    <div style="text-align:center; padding-top: 1rem">
        <img src="_static/backpop_logo.png" alt="BackPop Logo" style='width:100%; max-width: 700px'>
        <h4>A tool to sample the joint distributions of initial binary parameters and binary interaction assumptions</h4>
    </div>


.. test some code highlighting

.. code-block:: python

    from backpop import BackPop
    bp = BackPop(config_file="example.ini")
    posteriors = bp.run_sampler()
    posteriors.cornerplot()

.. toctree::
   :maxdepth: 10
   :hidden:

   pages/install
   pages/getting_started
   pages/tutorials
   pages/modules
   pages/cite
