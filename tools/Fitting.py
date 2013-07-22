'''
Created on 30 Oct 2012

@author: kreczko
'''

from ROOT import TMinuit, TMath, Long, Double
from array import array
import math
import logging
#from scipy.optimize import curve_fit

class TemplateFit():
    def __init__(self, histograms, data_label='data'):
        self.performedFit = False
        self.results = {}
        self.normalisation = {}
        self.normalisation_errors = {}
        self.data_label = data_label
        self.histograms = histograms
        self.templates = {}
        self.module = None
        # samples = all inputs except data
        keys = sorted(histograms.keys())
        keys.remove(data_label)
        self.samples = keys
        
        self.templates, self.normalisation, self.normalisation_errors = TemplateFit.generateTemplatesAndNormalisation(histograms)
        self.vectors = TemplateFit.vectorise(self.templates)
        self.param_indices = {}
        #check for consistency
        #vectos and templates all same size!!
        data_length = len(self.vectors[data_label])
        error = False
        for sample in self.vectors.keys():
            current_length = len(self.vectors[sample])
            if not data_length == current_length:
                if current_length < data_length:
                    for entry in range(current_length, data_length):
                        self.vectors[sample].append(0.)
                else:
                    print 'Error:'
                    print 'Sample "', sample, '" has different length'
                    print 'Expected:', data_length, ', found:', current_length
                    error = True
        if error:
            import sys
            sys.exit(-1)
        
    @staticmethod
    def generateTemplatesAndNormalisation(histograms):
        normalisation = {}
        normalisation_errors = {}
        templates = {}
        for sample, histogram in histograms.iteritems():
            normalisation[sample] = histogram.Integral()
            normalisation_errors[sample] = sum(histogram.errors())
            temp = histogram.Clone(sample + '_' + 'template')
            nEntries = temp.Integral()
            if not nEntries == 0:
                temp.Scale(1 / nEntries)
            templates[sample] = temp
        return templates, normalisation, normalisation_errors
            
    @staticmethod
    def vectorise(histograms):
        values = {}
        for sample in histograms.keys():
            hist = histograms[sample]
            nBins = hist.GetNbinsX()
            for bin_i in range(1, nBins + 1):
                if not values.has_key(sample):
                    values[sample] = []
                values[sample].append(hist.GetBinContent(bin_i))
        return values
        
class TMinuitFit(TemplateFit):
    
    fitfunction = None
    
    def __init__(self, histograms={}, dataLabel='data', method='logLikelihood'):
        TemplateFit.__init__(self, histograms, dataLabel)
        self.method = method
        self.logger = logging.getLogger('TMinuitFit')
        self.constraints = {}
        self.constraint_type = ''
        
    def fit(self):
        numberOfParameters = len(self.samples)
        gMinuit = TMinuit(numberOfParameters)
        if self.method == 'logLikelihood':  # set function for minimisation
            gMinuit.SetFCN(self.logLikelihood)
        gMinuit.SetPrintLevel(-1)
        # Error definition: 1 for chi-squared, 0.5 for negative log likelihood
        gMinuit.SetErrorDef(1)
        # error flag for functions passed as reference.set to as 0 is no error
        errorFlag = Long(2)
        
        N_total = self.normalisation[self.data_label] * 2
        N_min = 0
        
        param_index = 0
        for sample in self.samples:  # all samples but data
            gMinuit.mnparm(param_index, sample, self.normalisation[sample], 10.0, N_min, N_total, errorFlag)
            param_index += 1
        
        
#        N_signal = self.normalisation['signal']
#        gMinuit.mnparm(0, "N_signal(ttbar+single_top)", N_signal, 10.0, N_min, N_total, errorFlag)
#        gMinuit.mnparm(1, "bkg1", 10, 10.0, N_min, N_total, errorFlag)
        
        arglist = array('d', 10 * [0.])
        # minimisation strategy: 1 standard, 2 try to improve minimum (a bit slower)
        arglist[0] = 2
        # minimisation itself
        gMinuit.mnexcm("SET STR", arglist, 1, errorFlag)
        gMinuit.Migrad()
        self.module = gMinuit
        self.performedFit = True
        
        if not self.module:
            raise Exception('No fit results available. Please run fit method first')
        
        results = {}
        param_index = 0
        for sample in self.samples:
            temp_par = Double(0)
            temp_err = Double(0)
            self.module.GetParameter(param_index, temp_par, temp_err)
            if (math.isnan(temp_err)):
                self.logger.warning('Template fit error is NAN, setting to sqrt(N).')
                temp_err = math.sqrt(temp_par)
            
            results[sample] = (temp_par, temp_err)
            param_index += 1
        
        self.results = results
    
    def logLikelihood(self, nParameters, gin, f, par, iflag):
        lnL = 0.0
        data_vector = self.vectors[self.data_label]
        
        vector_entry = 0
        for data in data_vector:
            x_i = 0
            param_index = 0
            for sample in self.samples:
                x_i += par[param_index] * self.vectors[sample][vector_entry]
                self.param_indices[sample] = param_index
                param_index += 1
            data_i = self.normalisation[self.data_label] * data
            if not data == 0 and not x_i == 0:
                L = TMath.Poisson(data_i, x_i)
                lnL += TMath.log(L)
            
            
            
            vector_entry += 1
        
        f[0] = -2.0 * lnL
        
        #Adding the QCD and V+jets constraints
        if self.constraint_type == 'normalisation':
            f[0] += self.get_fit_normalisation_constraints(par)

    def readResults(self):
        return self.results
    
    # constraints = {sample: constraint}
    def set_fit_constraints(self, constraints, constraint_type = 'normalisation'):
        self.constraints = constraints
        self.constraint_type = constraint_type
    
    def get_fit_normalisation_constraints(self, params):
        result = 0
        for sample, constraint in self.constraints.iteritems():
            if self.normalisation[sample] != 0:
                result += (params[self.param_indices[sample]] - self.normalisation[sample]) ** 2 / (constraint * self.normalisation[sample]) ** 2
        return result
#class CurveFit():
#    defined_functions = ['gaus', 'gauss'] 
#    
#    @staticmethod
#    def gauss(x, *p):
#        A, mu, sigma = p
#        return A*numpy.exp(-(x-mu)**2/(2.*sigma**2))
#    
#    @staticmethod
#    def fit(hist, function, params):
#        if type(function) == type('s'):#string input
#            if not function in CurveFit.defined_functions:
#                raise Exception('Unknown function')
#            if function == 'gaus' or function == 'gauss':
#                function = CurveFit.gauss
#        x,y = list(hist.x()), list(hist.y())
#        
#        coeff, var_matrix = curve_fit(function, x, y, p0=params)
#        print coeff, var_matrix
#        #this should be transferred into rootpy.TF1
#        hist_fit = function(x, *coeff)
#        return hist_fit, x
