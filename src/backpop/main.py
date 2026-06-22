import numpy as np
import pandas as pd

from scipy.stats import multivariate_normal
import os.path

from cosmic import _evolvebin, evolve
from cosmic.consts import ALL_COLUMNS, INTEGER_COLUMNS, BPP_COLUMNS, BCM_COLUMNS, KICK_COLUMNS, GROUPED_SETTINGS
from nautilus import Prior, Sampler

from .files import parse_inifile
from .phase import select_phase, add_vsys_from_kicks
from .posteriors import BackPopsteriors


__all__ = ["BackPop"]


# remove bin_num from kick_columns and calculate shape
KICK_COLUMNS = [col for col in KICK_COLUMNS if col != "bin_num"]
KICK_SHAPE = (2, len(KICK_COLUMNS))

NATAL_KICK_TRANSLATOR = {
    "vk": 0,
    "phi": 1,
    "theta": 2,
    "omega": 3
}

EXTRA_PHASE_TABLE_COLS = ["vsys_1_total", "vsys_2_total"]


class BackPop():
    """Class to sample the joint distributions of initial binary parameters and binary interaction
    assumptions using Nautilus and COSMIC.

    Parameters
    ----------
    config_file : str, optional
        Path to INI file containing configuration parameters. Default is 'params.ini'.
    
    Attributes
    ----------
    config_file : str
        Path to INI file containing configuration parameters.
    flags : dict
        Dictionary of COSMIC flags to be set before evolving each binary.
    config : dict
        Dictionary of backpop configuration parameters.
    obs : dict
        Dictionary of observational constraints including means, sigmas, names, and output names. Names
        correspond to the internal COSMIC fortran names, while out_names correspond to the names in the output
        BPP array.
    var : dict
        Dictionary of parameters to vary including min, max, and names. Names correspond to the COSMIC fortran
        variable names.
    fixed : dict
        Dictionary of fixed parameters and their values. Names correspond to the COSMIC fortran variable names
    rv : scipy.stats.rv_continuous
        A scipy.stats continuous random variable object representing the likelihood function to evaluate
        the output parameters against.
    prior : nautilus.Prior
        Nautilus Prior object representing the prior distributions of the parameters to be varied.
    sampler : nautilus.Sampler
        Nautilus Sampler object used to perform the sampling.
    """
    def __init__(self, config_file='params.ini'):
        
        self.config_file = config_file

        # parse the configuration ini file, set flags and config
        self.config, self.flags, self.SSEDict, self.obs, self.var, self.fixed = parse_inifile(self.config_file)
        self.init_flags = self.flags.copy()
        if self.config["verbose"]:
            print(f"Initializing BackPop with {os.path.split(config_file)[-1]}")

        # create a scipy rv object for the likelihood
        # NOTE: currently assumes independent Gaussians (no correlated noise)
        self.rv = multivariate_normal(
            mean=np.array(self.obs["mean"]),
            cov=np.diag(np.array(self.obs["sigma"])**2)
        )
        
        # initialise the Nautilus prior
        self.prior = Prior()
        for i in range(len(self.var["name"])):
            self.prior.add_parameter(self.var["name"][i], dist=(self.var["min"][i], self.var["max"][i]))

        self.BPP_FLAT_LENGTH = self.config["n_bpp_rows"] * len(self.config["bpp_columns"])
        self.KICK_INFO_FLAT_LENGTH = np.prod(KICK_SHAPE)
        self.BCM_ROW_FLAT_LENGTH = len(self.config["bcm_columns"]) + len(EXTRA_PHASE_TABLE_COLS)
        self.BLOB_LENGTH = self.BPP_FLAT_LENGTH + self.KICK_INFO_FLAT_LENGTH + self.BCM_ROW_FLAT_LENGTH
        self.INVALID_LIKELIHOOD = (-np.inf, np.full(self.BLOB_LENGTH, np.nan, dtype=float))
        
    
    def run_sampler(self):
        """Run the Nautilus sampler to sample the joint distribution of initial binary parameters
        and binary interaction assumptions."""
        if self.config["verbose"]:
            print(f"Running sampling using multiprocessing with {self.config['n_threads']} threads")
    
        if self.config["output_folder"] != "" and self.config["output_folder"] != "None":
            filepath = os.path.join(self.config["output_folder"], 'samples_out.hdf5')
        else:
            output_path = os.path.join(os.getcwd(), 'output_folder')
            # check if output folder exists, if not create it
            if not os.path.exists(output_path):
                os.mkdir(output_path)
                if self.config["verbose"]:
                    print(f"Created output folder here: {output_path}")
            filepath = os.path.join(output_path, 'samples_out.hdf5')
            
        self.sampler = Sampler(
            prior=self.prior, 
            likelihood=self.likelihood, 
            n_live=self.config["n_live"], 
            pool=self.config["n_threads"],
            blobs_dtype=('blob', float, self.BLOB_LENGTH),
            filepath=filepath, 
            resume=self.config["resume"]
        )
        
        self.sampler.run(n_eff=self.config["n_eff"], verbose=self.config["verbose"], discard_exploration=True)

        points, log_w, log_l, blobs = self.sampler.posterior(return_blobs=True)

        # get back the flat arrays
        bpp_flat = blobs["blob"][:, :self.BPP_FLAT_LENGTH]
        kick_flat = blobs["blob"][:, self.BPP_FLAT_LENGTH:self.BPP_FLAT_LENGTH + self.KICK_INFO_FLAT_LENGTH]
        bcm_flat  = blobs["blob"][:, self.BPP_FLAT_LENGTH + self.KICK_INFO_FLAT_LENGTH:]
        del blobs

        bpp = pd.DataFrame(bpp_flat.reshape(-1, len(self.config["bpp_columns"])), columns=self.config["bpp_columns"])
        kick_info = pd.DataFrame(kick_flat.reshape(-1, KICK_SHAPE[-1]), columns=KICK_COLUMNS)
        bcm_row = pd.DataFrame(bcm_flat.reshape(-1, len(self.config["bcm_columns"]) + len(EXTRA_PHASE_TABLE_COLS)),
                               columns=self.config["bcm_columns"] + EXTRA_PHASE_TABLE_COLS)

        # set index so we can easily filter based on binaries
        bpp.index = np.repeat(np.arange(bpp.shape[0] / self.config["n_bpp_rows"]), self.config["n_bpp_rows"]).astype(int)
        kick_info.index = np.repeat(np.arange(kick_info.shape[0] / KICK_SHAPE[0]), KICK_SHAPE[0]).astype(int)
        bcm_row.index = np.arange(bcm_row.shape[0])
        
        # add bin_num
        bpp["bin_num"] = bpp.index
        kick_info["bin_num"] = kick_info.index
        bcm_row["bin_num"] = bcm_row.index

        # filter out empty data (evol_type would never be 0 in a real binary)
        bpp = bpp[bpp["evol_type"] > 0.0]

        posteriors = BackPopsteriors(points=points, log_w=log_w, log_l=log_l, var_names=self.var["name"],
                                     bpp=bpp, kick_info=kick_info, bcm_row=bcm_row)

        if self.config["output_folder"] != "" and self.config["output_folder"] != "None":
            posteriors.save(file=os.path.join(self.config["output_folder"], 'posteriors.h5'))
        else:
            posteriors.save(file=os.path.join(output_path, 'posteriors.h5'))

    def likelihood(self, x):
        '''Calculate the log-likelihood of a binary.
        
        Calculate the log-likelihood of a binary given prior bounds and input parameters
        using COSMIC to evolve the binary, select the phase of interest, and compare to
        observed binary properties.

        Parameters
        ----------
        x : dict
            Dictionary of input parameters that will be sampled by Nautilus
        
        Returns
        -------
        ll : float
            The log-likelihood of the binary given the input parameters and priors
        bpp_flat : :class:`~numpy.ndarray`
            Flattened array of the full BPP output from COSMIC
        kick_flat : :class:`~numpy.ndarray`
            Flattened array of the full kick info output from COSMIC
        '''
        # ensure that if m1 and m2 are both provided, m1 >= m2
        if "m1" in x and "m2" in x:
            if x["m1"] < x["m2"]:
                return self.INVALID_LIKELIHOOD

        # enforce limits on physical values
        # TODO: check with Katie if this is necessary with Nautilus priors
        for i, name in enumerate(x):
            val = x[name]
            if val < self.var["min"][i] or val > self.var["max"][i]:
                return self.INVALID_LIKELIHOOD

        # turn sampled log-parameters back into linear space if necessary
        for i, name in enumerate(x):
            if self.var["log"][i]:
                x[name] = 10**x[name]

        # evolve the binary
        result = self.evolv2(x)

        # check result and calculate likelihood
        if result[0] is None:
            return self.INVALID_LIKELIHOOD

        # apply log values to observed parameters if necessary
        for i, name in enumerate(self.obs["name"]):
            if self.obs["log"][i]:
                result[0][i] = np.log10(result[0][i])

        ll = np.sum(self.rv.logpdf(result[0]))

        # flatten arrays and force dtype
        bpp_flat = np.array(result[1], dtype=float).ravel()
        kick_flat = np.array(result[2], dtype=float).ravel()
        bcm_row = np.array(result[3], dtype=float).ravel()
        blob = np.concatenate([bpp_flat, kick_flat, bcm_row])
        
        # return the log-likelihood and flattened arrays as a single blob
        return ll, blob
    
    def evolv2(self, params_in):
        '''Evolve a binary with COSMIC given input parameters and return the output parameters
        at the time of the first BBH merger, as well as the full BPP and kick arrays.

        Parameters
        ----------
        params_in : dict
            Dictionary of input parameters that will be sampled by Nautilus
        
        Returns
        -------
        out : :class:`~pandas.DataFrame` or None
            DataFrame of output parameters at the time of the selected phase, or None if
            the phase was not reached
        bpp : :class:`~numpy.ndarray` or None
            Full BPP array from COSMIC, or None if the phase was not reached
        kick_info : :class:`~numpy.ndarray` or None
            Full kick info array from COSMIC, or None if the phase was not reached
        '''
        
        # handle initial binary parameters first, ensure all have been provided somewhere
        for param in ["m1", "m2", "tb", "e", "metallicity", "tphys"]:
            if param not in params_in and param not in self.fixed:
                raise ValueError(f"You must provide an input value for {param} "
                                 "either as a variable or fixed parameter")
            
        # set values for the evolvebin call
        m1 = params_in["m1"] if "m1" in params_in else self.fixed["m1"]
        m2 = params_in["m2"] if "m2" in params_in else self.fixed["m2"]
        m2, m1 = np.sort([m1,m2],axis=0)
        tb = params_in["tb"] if "tb" in params_in else self.fixed["tb"]
        e = params_in["e"] if "e" in params_in else self.fixed["e"]
        metallicity = params_in["metallicity"] if "metallicity" in params_in else self.fixed["metallicity"]
        tphysf = params_in["tphys"] if "tphys" in params_in else self.fixed["tphys"]

        # set the other flags
        self.set_flags(params_in)
        self.set_evolvebin_flags()
        self.set_SSEDict_flags()
        
        # set evolvebin to only use specific bpp and bcm columns
        bpp_columns = self.config["bpp_columns"]
        bcm_columns = self.config["bcm_columns"]
        
        col_inds_bpp = np.zeros(len(ALL_COLUMNS), dtype=int)
        col_inds_bpp[:len(bpp_columns)] = [ALL_COLUMNS.index(col) + 1 for col in bpp_columns]
        n_col_bpp = len(bpp_columns) 

        col_inds_bcm = np.zeros(len(ALL_COLUMNS), dtype=int)
        col_inds_bcm[:len(bcm_columns)] = [ALL_COLUMNS.index(col) + 1 for col in bcm_columns]
        n_col_bcm = len(bcm_columns)
        
        _evolvebin.col.n_col_bpp = n_col_bpp
        _evolvebin.col.col_inds_bpp = col_inds_bpp
        _evolvebin.col.n_col_bcm = n_col_bcm
        _evolvebin.col.col_inds_bcm = col_inds_bcm

        # most inputs start as a pair of zeros
        pair_vars = ["epoch", "ospin", "rad", "lumin", "massc", "radc",
                     "menv", "renv", "B_0", "bacc", "tacc", "tms", "bhspin"]
        p = {var: np.zeros(2) for var in pair_vars}

        # masses and kstars are actually set
        p["mass"] = np.array([m1, m2])
        p["mass0"] = np.array([m1, m2])
        p["kstar"] = np.array([1, 1])
        
        # setup the inputs for _evolvebin
        zpars = np.zeros(20)
        tphys = 0.0
        kick_info = np.zeros((2, 19))

        # only use detailed output when use_bcm is True
        dtp = 0.0 if self.config["use_bcm"] else 13700

        # run COSMIC!
        [zpars, kick_info_arrays, bpp_index, bcm_index] = _evolvebin.evolv2(p["kstar"], p["mass"], tb, e,
                                                                     metallicity, tphysf, dtp, p["mass0"],
                                                                     p["rad"], p["lumin"], p["massc"],
                                                                     p["radc"], p["menv"], p["renv"],
                                                                     p["ospin"], p["B_0"], p["bacc"],
                                                                     p["tacc"], p["epoch"], p["tms"],
                                                                     p["bhspin"], tphys, zpars, kick_info)

        if bpp_index < 0:
            raise ValueError("Failed in METISSE_zcnsts")
        else:
            bpp = _evolvebin.binary.bpp[:self.config["n_bpp_rows"], :n_col_bpp].copy()
            _evolvebin.binary.bpp[:bpp_index, :n_col_bpp] = np.zeros((bpp_index, n_col_bpp))
            
            bcm = _evolvebin.binary.bcm[:bcm_index, :n_col_bcm].copy()
            _evolvebin.binary.bcm[:bcm_index, :n_col_bcm] = np.zeros((bcm_index, n_col_bcm))

            # convert COSMIC output into dataframes
            bpp = pd.DataFrame(bpp, columns=bpp_columns, index=bpp[:, -1].astype(int))
            bcm = pd.DataFrame(bcm, columns=bcm_columns, index=bcm[:, -1].astype(int))
            kick_info = pd.DataFrame(kick_info_arrays, columns=KICK_COLUMNS,
                                     index=kick_info_arrays[:, -1].astype(int))
            
            # append kicks to either the bpp or bcm depending on what the use wants to use
            phase_table = add_vsys_from_kicks(bcm if self.config["use_bcm"] else bpp, kick_info)

            # select the phase of interest from the phase table using the user-defined condition
            out = select_phase(phase_table, condition=self.config["phase_condition"])

            if len(out) > 0:

                # check for MRR for DCO - phase select
                # obs_out = out[self.obs["out_name"]]

                # if obs_out["mass_1"].iloc[0] < obs_out["mass_2"].iloc[0]:
                #     m1_col = obs_out.pop("mass_2")
                #     m2_col = obs_out.pop("mass_1")
                #     obs_out.insert(0, "mass_1", m1_col)
                #     obs_out.insert(1, "mass_2", m2_col)

                # print(f'Found a binary that meets the phase condition! m1={m1:1.2f}, m2={m2:1.2f}, tb={tb:1.2f}, e={e:1.2f}, tphysf={tphysf:1.2f}, vsys_2_total ={out["vsys_2_total"].iloc[0]:1.2f}, teff_2 = {out["teff_2"].iloc[0]:1.2f}, log_lum_2 = {np.log10(out["lum_2"].iloc[0]):1.2f}')
                bcm_row = out.iloc[0].to_numpy() if self.config["use_bcm"] else np.zeros(len(bcm_columns) + len(EXTRA_PHASE_TABLE_COLS))
                return out[self.obs["out_name"]].iloc[0].to_numpy(), bpp.to_numpy(), kick_info.to_numpy(), bcm_row
            
            else:
                return None, None, None


    def set_flags(self, params_in):
        '''update dictionary of COSMIC flags with input parameters
        '''
        natal_kick = np.zeros((2,5))
        qcrit_array = np.zeros(16)
        qc_list = ["qMSlo", "qMS", "qHG", "qGB", "qCHeB", "qAGB", "qTPAGB", "qHeMS", "qHeGB", "qHeAGB"]

        # update flags based on input params
        for param in params_in.keys():
            # create natal kick arrays for each star if necessary
            if param in ["vk1", "phi1", "theta1", "omega1", "vk2", "phi2", "theta2", "omega2"]:
                param_name = param[:-1]
                param_star = int(param[-1]) - 1
                natal_kick[param_star, NATAL_KICK_TRANSLATOR[param_name]] = params_in[param]
            # same for qcrit_arrays
            elif param in qc_list:
                ind_dict = {}
                for k, v in zip(qc_list, range(0,10)):
                    ind_dict[v] = k
                qcrit_array[ind_dict[param]] = params_in[param]
            # otherwise just set the flag
            else:
                self.flags[param] = params_in[param]

        # if we set any of the arrays, update the flags
        if np.any(qcrit_array != 0.0):
            self.flags["qcrit_array"] = qcrit_array   
        if np.any(natal_kick != 0.0):
            self.flags["natal_kick_array"] = natal_kick


    def set_evolvebin_flags(self):
        '''Set the flags in the _evolvebin Fortran module from a dictionary of flags
        
        Parameters
        ----------
        flags : dict
            Dictionary of COSMIC flags to be passed to COSMIC
        '''
        # the following is equivalent to _evolvebin.windvars.neta = flags["neta"], etc
        for g in GROUPED_SETTINGS:
            for k in GROUPED_SETTINGS[g]:
                if k not in self.flags:
                    raise ValueError(f"flag {k} not found in flags dictionary")
                if k == "randomseed":
                    setattr(getattr(_evolvebin, g), "idum1", self.flags[k])
                else:
                    setattr(getattr(_evolvebin, g), k.lower(), self.flags[k])
        return None
    
    def set_SSEDict_flags(self):
        '''
        Set the SSE flags in the _evolvebin Fortran module from a dictionary of flags

        Parameters
        ----------
        flags : dict
            Dictionary of SSE flags to be passed to COSMIC
        '''
        z_accuracy_limit = self.SSEDict.get("z_accuracy_limit", 1e-2)

        if self.SSEDict["stellar_engine"] == "metisse":
            _evolvebin.se_flags.using_metisse = 1
            _evolvebin.se_flags.using_sse = 0

            # check if the metallicity for the initialbinarytable changes
            # raise an error if all the metallicities are not the same
            if 'metallicity' not in self.fixed.keys():
                raise ValueError("All the metallicities in the initial binary table "
                                "must be the same if you are using the METISSE stellar engine.")
            
            # load in the METISSE files
            _ = evolve.read_tracks_for_METISSE(
                path_to_tracks = self.SSEDict['path_to_tracks'], 
                IBT_Z = self.fixed["metallicity"],
                z_accuracy_limit = z_accuracy_limit,
                is_he = False
                )

            if (self.SSEDict['path_to_he_tracks'] != ''):
                _ = evolve.read_tracks_for_METISSE(
                    path_to_tracks = self.SSEDict['path_to_he_tracks'],
                    IBT_Z = self.fixed["metallicity"],
                    z_accuracy_limit = z_accuracy_limit,
                    is_he = True
                    )
        
        elif self.SSEDict["stellar_engine"] == "sse":
            _evolvebin.se_flags.using_sse = 1
            _evolvebin.se_flags.using_metisse = 0

        else:
            raise ValueError("Use either 'sse' or 'metisse' as stellar engine")