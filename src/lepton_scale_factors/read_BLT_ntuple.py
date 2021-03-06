'''
Created on 6 Jun 2014

@author: senkin

Read the BLT ntuple and extract the trigger objects. Match them with reco objects, perform
tag and probe studies to estimate single lepton trigger efficiency.

'''
from config import CMS
from rootpy.io import File
from rootpy import asrootpy, ROOTError
from optparse import OptionParser

import matplotlib
matplotlib.use('AGG')

import rootpy.plotting.root2matplotlib as rplt
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from rootpy.plotting import Hist
from tools.ROOT_utililities import set_root_defaults
from tools.file_utilities import make_folder_if_not_exists
from tools.plotting import make_plot, Histogram_properties
from ROOT import TLorentzVector, TGraphAsymmErrors, TF1, TEfficiency

import numpy
from numpy import frompyfunc
from pylab import plot

from matplotlib import rc
rc( 'font', **CMS.font )
rc( 'text', usetex = True )

class Particle :    
    def __init__(self, px, py, pz, energy) : 
        self.lorentz = TLorentzVector(px, py, pz, energy)
        self.isolation = 99999
        self.ID = 0

    def set_isolation_and_id(self, isolation, ID):
        self.isolation = isolation
        self.ID = ID

    def Pt(self):
        return self.lorentz.Pt()

    def Eta(self):
        return self.lorentz.Eta()

#for reference (see https://github.com/BristolTopGroup/NTupleProduction/blob/master/python/BristolNTuple_TriggerObjects_cfi.py)
trigger_objects = ['TriggerObjectElectronLeg', 'TriggerObjectElectronIsoLeg', 'TriggerObjectHadronLeg',
                   'TriggerObjectHadronIsoLeg', 'TriggerObjectHadronPFIsoLeg', 'TriggerObjectMuon1',
                   'TriggerObjectMuon2', 'TriggerObjectMuon2p1', 'TriggerObjectQuadJets']

histograms = {'reco_Z_peak' : Hist(30, 0, 150, name='reco_Z_peak'),
              'hlt_Z_peak' : Hist(30, 0, 150, name='hlt_Z_peak'),
              'reco_lepton_multiplicity' : Hist(5, 0, 5, name='reco_N_leptons'),
              'hlt_lepton_multiplicity' : Hist(5, 0, 5, name='hlt_N_leptons'),
              'btag_multiplicity' : Hist(5, 0, 5, name='N btags'),
              'reco_signal_lepton_pt' : Hist(30, 0, 150, name='reco_signal_lepton_pt'),
              'hlt_signal_lepton_pt' : Hist(30, 0, 150, name='hlt_signal_lepton_pt'),
              'reco_signal_lepton_eta' : Hist(30, -3, 3, name='reco_signal_lepton_eta'),
              'hlt_signal_lepton_eta' : Hist(30, -3, 3, name='hlt_signal_lepton_eta'),
              'reco_probe_lepton_pt' : Hist(30, 0, 150, name='reco_probe_lepton_pt'),
              'hlt_probe_lepton_pt' : Hist(30, 0, 150, name='hlt_probe_lepton_pt'),
              'reco_probe_lepton_eta' : Hist(30, -3, 3, name='reco_probe_lepton_eta'),
              'hlt_probe_lepton_eta' : Hist(30, -3, 3, name='hlt_probe_lepton_eta'),
              'probe_passed_pt' : Hist(30, 0, 150, name='probe_passed_lepton_pt'),
              'probe_total_pt' : Hist(30, 0, 150, name='probe_total_lepton_pt'),
              'probe_passed_eta' : Hist(30, -3, 3, name='probe_passed_lepton_eta'),
              'probe_total_eta' : Hist(30, -3, 3, name='probe_total_lepton_eta'),
}

def get_parameters(trigger_under_study):
    x_limits = [10, 100]
    x_title = '$p_{\mathrm{T}}$(jet) [GeV]'
    #y_title = '$\epsilon$'
    y_title = 'Efficiency'
    fit_function = ''    
    fit_range = [-9999, 9999]
    
    if '_pt' in trigger_under_study:
        x_limits = [20, 100]
        x_title = '$p_{\mathrm{T}}$(l) [GeV]'
        fit_function = "[0]*exp([1]*exp([2]*x))"
        fit_range = [20, 100]
    elif '_eta' in trigger_under_study:
        x_limits = [-3, 3]
        x_title = '$\eta$(l)'
        fit_function = '[0]*x*x + [1]*x + [2]'
        #fit_function = '[2]'
        fit_range = [-3, 3]
    elif '_phi' in trigger_under_study:
        x_limits = [-4., 4.]
        x_title = '$\phi$(l)'
        fit_function = '[0]'
        fit_range = [-3.1, 3.1]
        
    return x_limits, x_title, y_title, fit_function, fit_range

def set_parameter_limits(trigger_under_study, fit):
    if '_pt' in trigger_under_study:
        fit.SetParLimits(0, 0.0, 1.0)
        fit.SetParLimits(1, -100000.0, -1.0)
        fit.SetParLimits(2, -2.0, -0.01)

    if '_eta' in trigger_under_study:
        fit.SetParLimits(0, -0.2, 0.0)
        fit.SetParLimits(1, -1.0, -1.0)
        fit.SetParLimits(2, 0.2, 1.1)

def get_fitted_function_str(fit, fit_function):
    decimals = 3
    function_str = fit_function
    function_str = function_str.replace('x*x', 'x^{2}')
    function_str = function_str.replace('[0]', str('%.2g' % fit.GetParameter(0)))
    #function_str = function_str.replace('[1]', str(round(fit.GetParameter(1), decimals)))
    function_str = function_str.replace('[1]', str('%.2g' % fit.GetParameter(1)))
    function_str = function_str.replace('[2]', str('%.2g' % fit.GetParameter(2)))
    function_str = function_str.replace('[3]', str('%.2g' % fit.GetParameter(3)))
    function_str = function_str.replace('[4]', str('%.2g' % fit.GetParameter(4)))
    print function_str
    function_str = function_str.replace('*', ' \\times ')
    function_str = function_str.replace('0 \\times x^{2}', '')
    function_str = function_str.replace('0 \\times x', '')
    function_str = function_str.strip()#remove whitespace 
    function_str = function_str.replace('+ -', '-')
    function_str = function_str.replace('- +', '-')
    function_str = function_str.replace('- -', '+')
    function_str = function_str.replace('+  +', '+')
    function_str = function_str.replace('1 \\times', '1.0 \\times')
    function_str = function_str.replace('e+0', '\\times 10^')
    function_str = function_str.replace('(1\\times', '(')
    function_str = function_str.replace('(-1\\times', '(-')
    if function_str.startswith('+'):
        function_str = function_str[1:]
            
    if 'exp' in function_str:
        function_str = function_str.replace('exp(', 'e^{\left(')
        function_str = function_str.replace(')', '\\right)}')
        
    function_str = '$' + function_str + '$'
    print function_str
    
    return function_str

def make_single_efficiency_plot(hist_passed, hist_total, efficiency, channel = 'electron'):
    global output_folder, output_formats

    x_limits, x_title, y_title, fit_function, fit_range = get_parameters(efficiency)

    plot_efficiency = asrootpy(TGraphAsymmErrors())
    plot_efficiency.Divide(hist_passed, hist_total, "cl=0.683 b(1,1) mode")

    fit_data = TF1("fit_data", fit_function, fit_range[0], fit_range[1])
    set_parameter_limits(efficiency, fit_data)
    try:
        plot_efficiency.Fit(fit_data, 'FECQ')
    except ROOTError, e:
        print e.msg
        pass
    plot_efficiency.SetMarkerSize(2)

    save_as_name = efficiency

    # plot with matplotlib
    plt.figure(figsize=(20, 16), dpi=200, facecolor='white')

    ax0 = plt.axes()
    ax0.minorticks_on()
    ax0.grid(True, 'major', linewidth=2)
    ax0.grid(True, 'minor')
    plt.tick_params(**CMS.axis_label_major)
    plt.tick_params(**CMS.axis_label_minor)
    
    ax0.xaxis.set_major_formatter(FormatStrFormatter('%d'))
    ax0.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
    ax0.xaxis.labelpad = 11
    #ax0.yaxis.labelpad = 20
    
    rplt.errorbar(plot_efficiency, xerr=True, emptybins=True, axes=ax0, marker = 'o', ms = 15, mew=3, lw = 2)
    
    ax0.set_xlim(x_limits)
    ax0.set_ylim([0.0,1.1])
    
    #add fits
    x = numpy.linspace(fit_data.GetXmin(), fit_data.GetXmax(), fit_data.GetNpx())
    function_data = frompyfunc(fit_data.Eval, 1, 1)
    plot(x, function_data(x), axes=ax0, color = 'red', linewidth = 2)
    
    
    plt.tick_params(**CMS.axis_label_major)
    plt.tick_params(**CMS.axis_label_minor)

    plt.xlabel(x_title, CMS.x_axis_title)
    plt.ylabel(y_title, CMS.y_axis_title)
    if channel == 'electron':
        plt.title(r'e+jets, CMS Preliminary, $\sqrt{s}$ = 7 TeV', CMS.title)
    else:
        plt.title(r'$\mu$+jets, CMS Preliminary, $\sqrt{s}$ = 7 TeV', CMS.title)
    plt.legend(['data', 'fit'], numpoints=1, loc='lower right', prop=CMS.legend_properties)

    
    #add fit formulas
    ax0.text(0.2, 0.15, '$\epsilon$ = ' + get_fitted_function_str(fit_data, fit_function),
        verticalalignment='bottom', horizontalalignment='left',
        transform=ax0.transAxes,
        color='red', fontsize=60, bbox = dict(facecolor = 'white', edgecolor = 'none', alpha = 0.5))

    plt.tight_layout()
    
    for output_format in output_formats:
        plt.savefig(output_folder + save_as_name + '.' + output_format)  

def getNBJets(event, channel = 'electron'):
    # Get csv discriminating variable
    # Vector of double
    getVar = event.__getattr__
    if channel == 'electron':
        jetCsvDiscrim = getVar('cleanedJetsPFlowEPlusJets.CombinedSecondaryVertexBJetTag')
    else:
        jetCsvDiscrim = getVar('cleanedJetsPFlowMuPlusJets.CombinedSecondaryVertexBJetTag')
    
    nBJets = 0
    nJets = 0
    for csv in jetCsvDiscrim:
        nJets += 1
        if csv > 0.679 :
            nBJets += 1
            pass
        pass
    
    if nBJets > nJets : 'PANIC'
    
    return nBJets

def match_four_momenta(four_momentum, four_momenta):
    best_index = len(four_momenta)
    matched_delta_R = 9999
    for index in range(len(four_momenta)):
        delta_R = four_momentum.lorentz.DeltaR(four_momenta[index].lorentz)
        if (delta_R < matched_delta_R):
            matched_delta_R = delta_R
            best_index = index
    return best_index, matched_delta_R

def is_Z_event(first_lepton, second_lepton):
    inv_mass = (first_lepton.lorentz+second_lepton.lorentz).M()
    if inv_mass > 60 and inv_mass < 120:
        return True
    else:
        return False

def make_plots(channel = 'electron'):
    make_single_efficiency_plot(histograms['probe_passed_pt'], histograms['probe_total_pt'], 'probe_efficiency_pt', channel)
    make_single_efficiency_plot(histograms['probe_passed_eta'], histograms['probe_total_eta'], 'probe_efficiency_eta', channel)

    if channel == 'electron':
        title_channel = 'e+jets'
    else:
        title_channel = '$\mu$+jets'
    histogram_properties = Histogram_properties()
    histogram_properties.name = 'btag_multiplicity'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'N btags'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['btag_multiplicity'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'reco_leptons_multiplicity'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'N reco leptons'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['reco_lepton_multiplicity'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'Z_mass_peak_reco'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'Inv. mass 2 reco leptons'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['reco_Z_peak'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'hlt_leptons_multiplicity'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'N HLT leptons'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['hlt_lepton_multiplicity'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'Z_mass_peak_hlt'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'Inv. mass 2 HLT leptons'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['hlt_Z_peak'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'reco_signal_lepton_pt'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'Reco signal lepton pt'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['reco_signal_lepton_pt'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'reco_signal_lepton_eta'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'Reco signal lepton eta'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['reco_signal_lepton_eta'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'hlt_signal_lepton_pt'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'HLT signal lepton pt'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['hlt_signal_lepton_pt'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'hlt_signal_lepton_eta'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'HLT signal lepton eta'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['hlt_signal_lepton_eta'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'reco_probe_lepton_pt'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'Reco probe lepton pt'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['reco_probe_lepton_pt'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'reco_probe_lepton_eta'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'Reco probe lepton eta'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['reco_probe_lepton_eta'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'hlt_probe_lepton_pt'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'HLT probe lepton pt'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['hlt_probe_lepton_pt'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

    histogram_properties = Histogram_properties()
    histogram_properties.name = 'hlt_probe_lepton_eta'
    histogram_properties.title = title_channel + ', CMS Preliminary, $\sqrt{s}$ = 7 TeV'
    histogram_properties.x_axis_title = 'HLT probe lepton eta'
    histogram_properties.y_axis_title = 'Events'
    make_plot(histograms['hlt_probe_lepton_eta'], 'data', histogram_properties, save_folder = output_folder, save_as = ['pdf'])

def passes_ID_and_iso(lepton, channel = 'electron'):
    if channel == 'electron':
        if lepton.isolation < 0.1 and lepton.ID > 0.5:
            return True
        else:
            return False
    else:
        if lepton.isolation < 0.12 and lepton.ID != 0:
            return True
        else:
            return False

if __name__ == '__main__':
    set_root_defaults()
    parser = OptionParser()
    parser.add_option("-p", "--path", dest="path", default='/hdfs/TopQuarkGroup/trigger_BLT_ntuples/',
                  help="set path to input BLT ntuples")
    parser.add_option("-o", "--output_folder", dest="output_folder", default='HLT_plots/',
                  help="set path to save tables")
    parser.add_option("-c", "--centre-of-mass-energy", dest="CoM", default=8, type=int,
                      help="set the centre of mass energy for analysis. Default = 8 [TeV]")
    parser.add_option("--channel", dest="channel", default='electron',
                      help="set the lepton channel, default: electron")

    (options, args) = parser.parse_args()
    channel = options.channel
    if channel == 'electron':
        output_folder = options.output_folder + '/electron/'
    else:
        output_folder = options.output_folder + '/muon/'
    make_folder_if_not_exists(output_folder)
    output_formats = ['pdf']

    if channel == 'electron':
        histFile = options.path + '/SingleElectron_2011_RunAB_trigger_study.root'
        input_file = File(histFile)
        tree = input_file.Get('rootTupleTreeEPlusJets/ePlusJetsTree')
        reco_leptons_collection = 'selectedPatElectronsLoosePFlow'
        trigger_object_lepton = 'TriggerObjectElectronIsoLeg'
    else:
        histFile = options.path + '/SingleMu_2011_RunAB_trigger_study.root'
        input_file = File(histFile)
        tree = input_file.Get('rootTupleTreeMuPlusJets/muPlusJetsTree')
        reco_leptons_collection = 'selectedPatMuonsLoosePFlow'
        trigger_object_lepton = 'TriggerObjectMuon2p1'
    

    print 'Number of events : ', tree.GetEntries()
    #print 'Number of events after some random selection :', tree.GetEntries('Event.M3.patMETsPFlow > 100')

    for event in tree:
        reco_leptons = []
        hlt_leptons = []
        getVar = event.__getattr__
        run_number = getVar('Event.Run')
        # print 'Run number: ', run_number
        histograms['btag_multiplicity'].Fill( getNBJets( event, channel ) )
        reco_leptons_px = getVar(reco_leptons_collection + '.Px')
        reco_leptons_py = getVar(reco_leptons_collection + '.Py')
        reco_leptons_pz = getVar(reco_leptons_collection + '.Pz')
        reco_leptons_E  = getVar(reco_leptons_collection + '.Energy')
        if channel == 'electron':
            reco_leptons_isolation = getVar(reco_leptons_collection + '.PFRelIso03RhoEA')
            reco_leptons_id = getVar(reco_leptons_collection + '.mvaTrigV0')
        else:
            reco_leptons_isolation = getVar(reco_leptons_collection + '.PFRelIso04DeltaBeta')
            reco_leptons_id = getVar(reco_leptons_collection + '.isPFMuon')
        assert reco_leptons_px.size() == reco_leptons_py.size() == reco_leptons_pz.size() == reco_leptons_E.size()
        for index in range(reco_leptons_E.size()):
            reco_lepton = Particle(reco_leptons_px[index], reco_leptons_py[index], reco_leptons_pz[index], reco_leptons_E[index])
            reco_lepton.set_isolation_and_id(reco_leptons_isolation[index], reco_leptons_id[index])
            reco_leptons.append(reco_lepton)
            if index != 0:
                histograms['reco_probe_lepton_pt'].Fill(reco_lepton.Pt())
                histograms['reco_probe_lepton_eta'].Fill(reco_lepton.Eta())

        histograms['reco_lepton_multiplicity'].Fill(len(reco_leptons))

        if len(reco_leptons) != 0:
            histograms['reco_signal_lepton_pt'].Fill(reco_leptons[0].Pt())
            histograms['reco_signal_lepton_eta'].Fill(reco_leptons[0].Eta())

        if len(reco_leptons) >= 2:
            histograms['reco_Z_peak'].Fill((reco_leptons[0].lorentz+reco_leptons[1].lorentz).M())

        hlt_leptons_px = getVar(trigger_object_lepton + '.Px')
        hlt_leptons_py = getVar(trigger_object_lepton + '.Py')
        hlt_leptons_pz = getVar(trigger_object_lepton + '.Pz')
        hlt_leptons_E =  getVar(trigger_object_lepton + '.Energy')
        assert hlt_leptons_px.size() == hlt_leptons_px.size() == hlt_leptons_pz.size() == hlt_leptons_E.size()
        for index in range(hlt_leptons_px.size()):
            hlt_lepton = Particle(hlt_leptons_px[index], hlt_leptons_py[index], hlt_leptons_pz[index], hlt_leptons_E[index])
            hlt_leptons.append(hlt_lepton)
            if index != 0:
                histograms['hlt_probe_lepton_pt'].Fill(hlt_lepton.Pt())
                histograms['hlt_probe_lepton_eta'].Fill(hlt_lepton.Eta())

        histograms['hlt_lepton_multiplicity'].Fill(len(hlt_leptons))
        
        if len(hlt_leptons) != 0:
            histograms['hlt_signal_lepton_pt'].Fill(hlt_leptons[0].Pt())
            histograms['hlt_signal_lepton_eta'].Fill(hlt_leptons[0].Eta())

        if len(hlt_leptons) >= 2:
            histograms['hlt_Z_peak'].Fill((hlt_leptons[0].lorentz+hlt_leptons[1].lorentz).M())

        event_has_Z_peak = False
        tag_matches_to_hlt_object = False
        last_probe_index = 0
        if len(reco_leptons) == 1:
            print 'Just one lepton in event!'
        if len(reco_leptons) > 1:
            for index in range(len(reco_leptons)):
                #assuming index=0 is the signal lepton (tag)
                matched_index_signal_lepton, matched_delta_R_signal_lepton = match_four_momenta(reco_leptons[0], hlt_leptons)
                tag_matches_to_hlt_object = matched_index_signal_lepton < 0.3
                if index != 0 and tag_matches_to_hlt_object and is_Z_event(reco_leptons[0], reco_leptons[index]):
                    event_has_Z_peak = True
                    matched_index, matched_delta_R = match_four_momenta(reco_leptons[index], hlt_leptons)
                    last_probe_index = index
                    if matched_delta_R < 0.3 and passes_ID_and_iso(reco_leptons[index], channel):
                        histograms['probe_passed_pt'].Fill(reco_leptons[index].Pt())
                        histograms['probe_passed_eta'].Fill(reco_leptons[index].Eta())
                        break
            if event_has_Z_peak and tag_matches_to_hlt_object and passes_ID_and_iso(reco_leptons[last_probe_index], channel):
                histograms['probe_total_pt'].Fill(reco_leptons[last_probe_index].Pt())
                histograms['probe_total_eta'].Fill(reco_leptons[last_probe_index].Eta())

        trigger_list = getVar('Trigger.HLTNames')
        trigger_results = getVar('Trigger.HLTResults')

        assert trigger_list.size() == trigger_results.size()
        # for index in range(trigger_list.size()):
        #     if not 'not found' in trigger_list[index]:
        #         print trigger_list[index], trigger_results[index]

    make_plots(channel = channel)



