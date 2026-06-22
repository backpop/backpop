import corner
import matplotlib.pyplot as plt
import numpy as np
import h5py as h5
import pandas as pd

from cosmic.consts import BPP_COLUMNS, KICK_COLUMNS, BCM_COLUMNS

__all__ = ['BackPopsteriors']

# remove bin_num from kick_columns and calculate shape
KICK_COLUMNS = [col for col in KICK_COLUMNS if col != "bin_num"]
KICK_SHAPE = (2, len(KICK_COLUMNS))

class BackPopsteriors():
    def __init__(self, file=None, points=None, log_w=None, log_l=None, var_names=None,
                 var_labels=None, bpp=None, kick_info=None, bcm_row=None):
        """Utility class to handle and analyse posterior samples from BackPop.

        Parameters
        ----------
        file : str, optional
            Path to an HDF5 file containing posterior samples. The file should contain datasets
            named 'points', 'log_w', 'log_l', 'var_names', and 'blobs'.
        points : ~numpy.ndarray, optional
            Array of shape (n_samples, n_vars) containing posterior samples.
        log_w : ~numpy.ndarray, optional
            Array of shape (n_samples,) containing log weights for each sample.
        log_l : ~numpy.ndarray, optional
            Array of shape (n_samples,) containing log likelihoods for each sample.
        var_names : list of str, optional
            List of variable names corresponding to the columns in `points`.
        var_labels : list of str, optional
            List of labels for the variables, used in plotting. If not provided, `var_names` will be used.
        bpp : pd.DataFrame, optional
            DataFrame containing binary population properties for each sample. Should have a 'bin_num' column
            that matches the index of the samples in `points`.
        kick_info : pd.DataFrame, optional
            DataFrame containing kick information for each sample. Should have a 'bin_num' column that matches the index of the samples in `points`.
        bcm_row : pd.DataFrame, optional
            DataFrame containing binary compact merger information for each sample. Should have a 'bin_num' column that matches the index of the samples in `points`.

        Raises
        ------
        ValueError
            If neither `file` nor all of `points`, `log_w`, `log_l`, and `var_names` are provided.
        """
        
        self.file = file
        self.bcm_row = None

        # load data from file if provided
        if file is not None:
            with h5.File(file, 'r') as f:
                self.points = f['points'][:]
                self.log_w = f['log_w'][:]
                self.log_l = f['log_l'][:]
                self.var_names = np.array(f['var_names'][:].astype(str).tolist())

                self.bpp = pd.read_hdf(file, key='bpp')
                self.kick_info = pd.read_hdf(file, key='kick_info')
                if 'bcm_row' in f:
                    self.bcm_row = pd.read_hdf(file, key='bcm_row')
                    
        # otherwise use provided data
        elif (points is not None and log_w is not None and log_l is not None and var_names is not None
              and bpp is not None and kick_info is not None and bcm_row is not None):
            self.points = points
            self.log_w = log_w
            self.log_l = log_l
            self.var_names = var_names
            self.bpp = bpp
            self.kick_info = kick_info
            self.bcm_row = bcm_row
            
        # or shout at the user
        else:
            raise ValueError("Must provide either a file or points, log_w, log_l, var_names, bpp, kick_info, and bcm_row.")

        self.labels = var_labels if var_labels is not None else self.var_names

    def __len__(self):
        return self.points.shape[0]

    def __repr__(self):
        return (f"<BackPopPosteriors: {self.points.shape[0]} samples, "
                f"{self.points.shape[1]} variables")
    
    @property
    def n_vars(self):
        return self.points.shape[1]

    def cornerplot(self, which_vars=None, extra_vars=None, extra_labels=None, show=True, **kwargs):
        """Create a corner plot of the posterior samples.

        Parameters
        ----------
        which_vars : ``list`` of ``str``, optional
            List of variable names to include in the corner plot. If None, all variables will be used.
            Default is None.
        show : ``bool``, optional
            Whether to display the plot immediately. Default is True.
        **kwargs : additional keyword arguments
            Additional keyword arguments to pass to `corner.corner()`. See the `corner` documentation
            for available options.
        """
        mask = np.ones(self.n_vars, dtype=bool)
        if which_vars is not None:
            mask = np.isin(self.var_names, which_vars)
            if not np.any(mask):
                raise ValueError("No matching variable names found.")
            
        likelihood_mask = np.isfinite(self.log_l)

        points = self.points[:, mask]
        labels = self.labels[mask]
        if extra_vars is not None and extra_labels is not None:
            # check that the shapes of extra_vars and extra_labels are correct
            extra_vars = np.atleast_2d(extra_vars)
            if extra_vars.shape[0] != self.points.shape[0]:
                raise ValueError("extra_vars must have the same number of rows as points.")
            if len(extra_labels) != extra_vars.shape[1]:
                raise ValueError("extra_labels must have the same length as the number of columns in extra_vars.")
            points = np.hstack([points, extra_vars])
            labels = np.hstack([labels, extra_labels])

        points = points[likelihood_mask]
        weights = np.exp(self.log_w[likelihood_mask])
        
        fig = corner.corner(
            points, weights=weights, bins=kwargs.pop("bins", 20),
            labels=labels, color=kwargs.pop("color", '#074662'),
            plot_datapoints=kwargs.pop("plot_datapoints", False),
            range=kwargs.pop("range", np.repeat(0.999, self.n_vars)), **kwargs); # this should handle the double plot

        if show:
            plt.show()
        return fig
    
    def save(self, file=None):
        """Save the posterior samples to an HDF5 file.

        Parameters
        ----------
        file : ``str``, optional
            Path to the output HDF5 file. If not provided, the file path used during initialization
            will be used.
        """
        
        if file is None and self.file is None:
            raise ValueError("Must provide a file path to save to.")
        elif file is None:
            file = self.file

        with h5.File(file, 'w') as f:
            f.create_dataset('points', data=self.points)
            f.create_dataset('log_w', data=self.log_w)
            f.create_dataset('log_l', data=self.log_l)
            f.create_dataset('var_names', data=[n for n in self.var_names])
        
        self.bpp.to_hdf(file, key='bpp')
        self.kick_info.to_hdf(file, key='kick_info')

        # save bcm only if use_bcm = True
        if np.all(self.bcm_row['tphys']) != 0: 
            self.bcm_row.to_hdf(file, key='bcm_row')

