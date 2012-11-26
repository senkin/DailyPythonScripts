'''
Created on 20 Nov 2012

@author: kreczko
'''
from tools.uncertainties import ufloat

def calculate_xsection(inputs, luminosity, efficiency = 1.):
    '''
    BUG: this doesn't work unless the inputs are unfolded!
    inputs = list of value-error pairs
    luminosity = integrated luminosity of the measurement
    '''
    result = []
    add_result = result.append
    for value, error in inputs:
        xsection = value / luminosity / efficiency
        xsection_error = error / luminosity / efficiency
        add_result((xsection, xsection_error))        
    return result

def calculate_normalised_xsection(inputs, bin_widths, normalise_to_one=False):
    '''
    Calculates normalised average x-section for each bin: 1/N *1/bin_width sigma_i
    There are two ways to calculate this
    1) N = sum(sigma_i)
    2) N = sum(sigma_i/bin_width)
    The latter one will normalise the total distribution to 1
    inputs = list of value-error pairs
    bin_widths = bin widths of the inputs
    '''
    result = []
    add_result = result.append
    
    normalisation = 0
    for measurement, bin_width in zip(inputs, bin_widths):
        value = ufloat(measurement)
        
        if normalise_to_one:
            normalisation += value / bin_width
        else:
            normalisation += value
    for measurement, bin_width in zip(inputs, bin_widths):
        value = ufloat(measurement)
        xsection = value / normalisation / bin_width
        add_result((xsection.nominal_value, xsection.std_dev()))   
    return result

def decombine_result(combined_result, original_ratio):
    '''
    Use to extract the individual results from a combined result
    i.e. 
    combined_result = (sample_1_value + sample_2_value, combined_error)
    original_ratio = sample_1_value/sample_2_value
    This method will return the decombined values for the two samples:
    return (sample_1_value, sample_1_error), (sample_2_value, sample_2_error)
    with the proper errors
    '''
    combined_result = ufloat(combined_result)
    sample_1 = combined_result * original_ratio/(1+original_ratio)
    sample_2 = combined_result - sample_1
    return (sample_1.nominal_value, sample_1.std_dev()), (sample_2.nominal_value, sample_2.std_dev())
