'''
Created on 31 Oct 2012

@author: kreczko
'''
availablemethods = [
#                     'RooUnfoldTUnfold', # not working under ROOT 6
                    'RooUnfoldBayes',
                    'RooUnfoldSvd',
                    'RooUnfoldBinByBin',
                    'RooUnfoldInvert',
                    'TSVDUnfold',
                    'TopSVDUnfold',
                    ]

SVD_k_value = 5
SVD_tau_value = -1
SVD_n_toy = 1000
Hreco = 2
Bayes_n_repeat = 4

unfolded_markerStyle = 20
unfolded_fillStyle = 0
unfolded_color = 'black'

truth_color = 'red'
truth_fillStyle = 0

measured_color = 'blue'
measured_fillStyle = 0
