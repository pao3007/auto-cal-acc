# -*- coding: utf-8 -*-
"""
Created on Fri Mar 25 08:38:43 2022

@author: ErayMyumyun
"""

from os import chdir as os_chdir
from os.path import isfile as os_path_isfile
from math import isnan as math_isnan, log2 as math_log2, ceil as math_ceil
import numpy as np
from scipy.signal import filtfilt as signal_filtfilt, butter as signal_butter, periodogram as signal_periodogram, \
    coherence as signal_coherence
import matplotlib.pyplot as plt
# from IPython.display import display
import SensAcc.AC_functions_1FBG_v2 as fun

class ACCalib_2ch:

    def __init__(self, ref_opt_name, Scriptpath, Main_folder_path, Opt_path, Ref_path, Ref_sensitivity, GainMark,
                 Opt_samp_freq, Ref_samp_freq, Filter_on, Downsample_ref, Do_spectrum, l_flatness,
                 r_flatness, AngleSetFreq, phase_mark):
        self.ref_opt_name = ref_opt_name
        # %% Location of data and scrips
        # Path where the scripts are  (AC_functions_1FBG_v2 and AC_calibration_1FBG_v2)
        self.Main_folder_path = Main_folder_path
        # Main path is where the sensitivities.csv and time_corrections.csv will be saved.
        # If sensitivities.csv and time_corrections.csv do not exist, they will be automatically generated
        self.Scriptpath = Scriptpath
        self.Opt_path = Opt_path
        self.Ref_path = Ref_path
        # %% Reference values
        # Ref_sensitivity = 1.048689
        # Ref_sensitivity = 1.079511
        # Ref_sensitivity = 0.010061
        self.Ref_sensitivity = Ref_sensitivity
        self.Opt_samp_freq = Opt_samp_freq #  800
        self.Ref_samp_freq = Ref_samp_freq #  12800
        self.l_flatness = l_flatness
        self.r_flatness = r_flatness
        self.AngleSetFreq = AngleSetFreq
        self.phase_mark = phase_mark
        # At which frequency to measure the sensitivity
        self.GainMark = GainMark  # Frequency at which sensitivity is determined, adjust as desired

        # Sampling frequencies of optical and reference signal

        # %% Optional settings
        # 1 if Enlight was used
        self.Enlight = 0

        # 1 if other software is used. Give how many rows need to be skipped in data file
        self.Else = 1
        self.skiprows = 4

        # 1 if Faz is used. Skiprows not used wih Faz, Faz does not add headers or anything else.
        self.Faz = 0

        # 1 to make plots, 0 to not make them

        # X axis limits
        self.xScale = [10, 400]  # Frequency spectrum x axis limit
        self.xScaleTransfer = [0, 400]  # Power spectrum and Bode analysis x-axis limit

        # 1 to filter signal, 0 to not filter
        if Filter_on == "highpass":
            self.Filter_on = 1
            # Cutoff frequenties for the filter. [lowend, highend]
            # If you want a lowpass filter change the lowend to 0 and if you want a highpass filter change the highend to 0.5*Ref_samp_freq
            self.CutOffOpt = [5, self.Opt_samp_freq / 2]
            self.CutOffRef = [5, self.Ref_samp_freq / 2]
            # CutOffOpt = [5, 400]
            # CutOffRef = [5, 400]
            print("high-pass")
        elif Filter_on == "lowpass":
            self.Filter_on = 1
            self.CutOffOpt = [0, self.Opt_samp_freq / 2 - 1]
            self.CutOffRef = [0, self.Ref_samp_freq / 2 - 1]
            print("low-pass")
        elif Filter_on == "bandpass":
            self.Filter_on = 1
            self.CutOffOpt = [5, self.Opt_samp_freq / 2 - 1]
            self.CutOffRef = [5, self.Ref_samp_freq / 2 - 1]
        else:
            self.Filter_on = 0

        # 1 to downsample reference signal to optical signal frequency,0 to upsample optical signal to reference signal frequency
        self.Downsample_ref = Downsample_ref

        # Necessary settings in normal calibration, can be disabled if desired
        self.Adjust_time_correction = 1
        self.Do_spectrum = Do_spectrum
        # 0 to obtain sensitivity from data file, enter value if other sensitivity is desired

    def start(self, make_plots, Set_sensitivity, Adjust_gain, add_time_correction):
    # Changes dir to where the scripts are saved. This way cells can be run without issue
        print("START CALIB SCRIPT")
        os_chdir(self.Scriptpath)
        acc_kalib = []

        # %% Load timeshifts and sensitivities
        # If timeshift and sensitivy file are present, they will be loaded, otherwise they will be created
        os_chdir(self.Main_folder_path)
        if os_path_isfile('time_corrections.csv') is False:
            time_corrections = -3 * np.ones((1 + 1, 1))
            time_corrections = time_corrections.reshape(len(time_corrections, ))
            np.savetxt('time_corrections.csv', time_corrections)
        else:
            time_corrections = np.loadtxt('time_corrections.csv')

        if os_path_isfile('sensitivities.csv') is False:
            sensitivities = 1e-10 * np.ones((1 + 1, 1))
            sensitivities = sensitivities.reshape(len(sensitivities, ))
            np.savetxt('sensitivities.csv', sensitivities)
        else:
            sensitivities = np.loadtxt('sensitivities.csv')
        # %% Checks if sensitivities.csv and time_corrections.csv are the correct size and if not, it corrects it

        # %% Data loading
        opt_file_name = self.ref_opt_name
        ref_file_name = self.ref_opt_name
        # display(['Analysing: ' + str(opt_file_name)])
        # If csv of data is present it will be loaded, otherwise data file will be analyzed and csv file with wavelengths will be created
        # Adjust functions depending on used interrogator software
        os_chdir(self.Opt_path)
        if os_path_isfile(opt_file_name + '.csv') is True:
            DataOptRel = np.loadtxt(opt_file_name + '.csv')
            # display(['Optical .csv file found'])
        else:
            # if self.Enlight == 1:
            #     display(['Optical .csv file not found. Creating .csv file ...'])
            #     DataOptRel = fun.read_Enlight_Data_AC(opt_file_name)
            #     np.savetxt(opt_file_name + '.csv', DataOptRel)
            #     display(['.csv file complete'])
            # if self.Faz == 1:
            #     display(['Optical .csv file not found. Creating .csv file ...'])
            #     DataOptRel = fun.read_txt_file(opt_file_name, 0)[0:, (8)] * 10 ** 9
            #     np.savetxt(opt_file_name + '.csv', DataOptRel)
            #     display(['.csv file complete'])
            if self.Else == 1:
                # display(['Optical .csv file not found. Creating .csv file ...'])
                DataOptRel = fun.read_txt_file_AC(opt_file_name, self.skiprows)
                np.savetxt(opt_file_name + '.csv', DataOptRel)
                # display(['.csv file complete'])

        # Loading of reference data, same as optical data

        os_chdir(self.Ref_path)
        if os_path_isfile(ref_file_name + '.csv') is True:
            DataRefRel = np.loadtxt(ref_file_name + '.csv')
            # display(['Reference .csv file found'])
        else:
            # display(['Reference .csv file not found. Creating .csv file ...'])
            DataRefRel = fun.read_txt_file(ref_file_name, 23)
            np.savetxt(ref_file_name + '.csv', DataRefRel)
            # display(['Reference .csv file done'])
        # %% Data Selection
        # Loads saved sensitivity for analyzing and adjusting
        if Set_sensitivity != 0:
            Sensitivity_opt = Set_sensitivity
            # Adjust_gain = False
        else:
            Sensitivity_opt = sensitivities[0]
            # Adjust_gain = True

        if math_isnan(Sensitivity_opt) == True:
            Sensitivity_opt = 1e-10

        # acc_kalib.append(round(np.mean(DataOptRel[0:100]), 5))
        cw1 = round(np.mean(DataOptRel[50:100, 0]), 5)

        cw2 = round(np.mean(DataOptRel[50:100, 1]), 5)
        acc_kalib.append(cw1)
        # display(['Center wavelength = ' + str(acc_kalib[0]) + ' and ' + str(round(np.mean(DataOptRel[50:100, 1]), 5)) + ' nm'])
        # Calculate acceleration from optical data and previously determined sensitivity

        optical_sensor_data = fun.calculateAC(-(DataOptRel[:, 0] -
                                                DataOptRel[:, 1]) +
                                              (cw1 - cw2), Sensitivity_opt)




        # optical_sensor_data = fun.calculateAC(-(DataOptRel[:, 0] - DataOptRel[:, 1]) +
        #                                       (round(np.mean(DataOptRel[100:200, 0]), 5) -
        #                                        round(np.mean(DataOptRel[100:200, 1]), 5)), Sensitivity_opt)
        # optical_sensor_data = fun.calculateAC(((DataOptRel[:,0]-acc_kalib[0])+(DataOptRel[:,1]-round(np.mean(DataOptRel[0:800, 1]), 5)))/2,
        #     Sensitivity_opt)
        # Calculate acceleration from reference data and corresponsing sensitivity for reference sensor
        # reference_sensor_data = DataRefRel / self.Ref_sensitivity

        reference_sensor_data = DataRefRel
        # DataRefRel[:, 1] / Ref_sensitivity

        def detect_max_in_first_second(data, sampling_rate):
            data_in_first_second = data[:int(sampling_rate*1.5)]
            return np.argmax(np.abs(data_in_first_second))

        opt_max_idx = detect_max_in_first_second(optical_sensor_data, self.Opt_samp_freq)
        ref_max_idx = detect_max_in_first_second(reference_sensor_data, self.Ref_samp_freq)

        opt_time = float(opt_max_idx) / float(self.Opt_samp_freq)
        ref_time = float(ref_max_idx) / float(self.Ref_samp_freq)

        ShiftLeft = (opt_time - ref_time)
        print("TIme shif : " + str(ShiftLeft))

        optical_sensor_data = optical_sensor_data[int(self.Opt_samp_freq*1.5):len(optical_sensor_data-1)]
        reference_sensor_data = reference_sensor_data[int(self.Ref_samp_freq*1.5):len(reference_sensor_data-1)]

        # reference_sensor_data = DataRefRel / self.Ref_sensitivity
        # %% Time Syncing
        # Creating time arrays for optical and reference signal according to sampling frequency
        TimeOpt = np.linspace(1 / self.Opt_samp_freq, len(optical_sensor_data) / self.Opt_samp_freq, num=len(optical_sensor_data))
        TimeRef = np.linspace(1 / self.Ref_samp_freq, len(reference_sensor_data) / self.Ref_samp_freq, num=len(reference_sensor_data))
        # Load timecorrection shift from file and adjust time of reference signal
        # ShiftLeft = -time_corrections[0]

        TimeRefShifted = TimeRef + ShiftLeft
        #
        # ShiftLeft = -add_time_correction
        # TimeRefShifted = TimeRef + add_time_correction
        # print("TimeRefShifted : " + str(TimeRefShifted))
        # %% Filtering
        # Currently bandpass filtering is used, if other form of filtering is desired, adjust cutoff frequency accordingly
        if self.Filter_on == 1:
            if self.CutOffOpt[0] == 0:
                B, A = signal_butter(3, self.CutOffOpt[1] / (0.5 * self.Opt_samp_freq), 'lowpass')
            else:
                if self.CutOffOpt[1] == 0.5 * self.Opt_samp_freq:
                    B, A = signal_butter(3, self.CutOffOpt[0] / (0.5 * self.Opt_samp_freq), 'highpass')
                else:
                    self.CutOffOpt = [self.CutOffOpt[0] / (0.5 * self.Opt_samp_freq), self.CutOffOpt[1] / (0.5 * self.Opt_samp_freq)]
                    B, A = signal_butter(3, self.CutOffOpt, 'bandpass')
            opt_sens_filtered = signal_filtfilt(B, A, optical_sensor_data)

            if self.CutOffRef[0] == 0:
                B, A = signal_butter(3, self.CutOffRef[1] / (0.5 * self.Ref_samp_freq), 'lowpass')
            else:
                if self.CutOffRef[1] == 0.5 * self.Ref_samp_freq:
                    B, A = signal_butter(3, self.CutOffRef[0] / (0.5 * self.Ref_samp_freq), 'highpass')
                else:
                    self.CutOffRef = [self.CutOffRef[0] / (0.5 * self.Ref_samp_freq), self.CutOffRef[1] / (0.5 * self.Ref_samp_freq)]
                    B, A = signal_butter(3, self.CutOffRef, 'bandpass')
            ref_sens_filtered = signal_filtfilt(B, A, reference_sensor_data)
        else:
            opt_sens_filtered = optical_sensor_data
            ref_sens_filtered = reference_sensor_data
        # %% Preparing data for bode analisis
        # Downsample reference signal to immitate nyquist effects.
        # Or upsample Optical signal for better time shift estimate.

        if self.Downsample_ref == 1:
            # Optical signal remains the same
            OptSensResampled = opt_sens_filtered
            TimeOptSensResampled = TimeOpt

            # Resampling reference signal through interpolation
            ref_sens_resampled = fun.resample_by_interpolation(ref_sens_filtered, self.Ref_samp_freq, self.Opt_samp_freq)
            ref_sens_resampled_time = fun.resample_by_interpolation(TimeRefShifted, self.Ref_samp_freq, self.Opt_samp_freq)

            # Determining sample difference and resizing signals accordingly
            SampleDiff = round(ShiftLeft * self.Opt_samp_freq)
            OptSensResized, RefSensResized = fun.SignalResize(OptSensResampled, ref_sens_resampled, SampleDiff)

            # Creating of new time arrays according to resize signal length and sampling frequency
            TimeOptSensResized = np.linspace(1 / self.Opt_samp_freq, len(OptSensResized) / self.Opt_samp_freq, num=len(OptSensResized))
            TimeRefSensResized = np.linspace(1 / self.Opt_samp_freq, len(RefSensResized) / self.Opt_samp_freq, num=len(RefSensResized))
            BodeSampFreq = self.Opt_samp_freq
        else:
            # Resampling optical signal through interpolation
            OptSensResampled = fun.resample_by_interpolation(opt_sens_filtered, self.Opt_samp_freq, self.Ref_samp_freq)
            TimeOptSensResampled = fun.resample_by_interpolation(TimeOpt, self.Opt_samp_freq, self.Ref_samp_freq)

            # Reference signal remains the same
            ref_sens_resampled = ref_sens_filtered
            ref_sens_resampled_time = TimeRefShifted

            # Determining sample difference and resizing signals accordingly
            SampleDiff = round(ShiftLeft * self.Ref_samp_freq)
            OptSensResized, RefSensResized = fun.SignalResize(OptSensResampled, ref_sens_filtered, SampleDiff)

            # Creating of new time arrays according to resize signal length and sampling frequency
            TimeOptSensResized = np.linspace(1 / self.Ref_samp_freq, len(OptSensResized) / self.Ref_samp_freq, num=len(OptSensResized))
            TimeRefSensResized = np.linspace(1 / self.Ref_samp_freq, len(RefSensResized) / self.Ref_samp_freq, num=len(RefSensResized))
            BodeSampFreq = self.Ref_samp_freq
        # %% Fourier analysis
        # display(['Computing Fourier Analisis...'])
        # Estimating power spectral density through periodogram function
        if self.Do_spectrum == 1:
            FreqOptPSD, OptPSD = signal_periodogram(OptSensResized, BodeSampFreq)
            FreqRefPSD, RefPSD = signal_periodogram(RefSensResized, BodeSampFreq)
        else:
            FreqOptPSD, OptPSD = 0, 0
            FreqRefPSD, RefPSD = 0, 0

        # Creating a low pass filter for smoothening graphs. The "10" below is the frequency
        Smooth_freq = [1 / (0.5 * self.Opt_samp_freq)]
        B, A = signal_butter(3, Smooth_freq, 'lowpass')

        # Smoothening FreqOptPSD and FreqRefPSD
        SmoothOptPSD = signal_filtfilt(B, A, OptPSD)
        SmoothRefPSD = signal_filtfilt(B, A, RefPSD)

        # Smootheing of signals transfer function through lowpass filter
        NFFT = 2 ** math_ceil(math_log2(abs(len(OptSensResized))))

        # Determining of transfer function to be smoothened
        Transfer, FreqTransfer = fun.FourierAnalisis(RefSensResized, OptSensResized, BodeSampFreq)

        # Smoothening the signal with a lowpass.
        SmoothTransfer = signal_filtfilt(B, A, abs(Transfer))

        # Estimate the magnitude squared coherence estimate of the signals
        FreqCoherence, Coherence = signal_coherence(RefSensResized, OptSensResized, fs=BodeSampFreq, nperseg=round(NFFT / 20),
                                                    noverlap=round(NFFT / 40), nfft=NFFT)

        # Smootheing of coherence array
        SmoothCoherence = signal_filtfilt(B, A, Coherence)
        # %% Determine gain at set frequency
        GainAtMark = fun.interp1_for_remco(FreqTransfer, SmoothTransfer, self.GainMark)
        # Convert gain to sensitivity and save for further use

        offset = 0
        if Adjust_gain:
            sensitivities[0] = Sensitivity_opt * GainAtMark
            Sensitivity_opt = sensitivities[0]
            acc_kalib.append(sensitivities[0] * 1000.0)
            offset = round(cw2 - cw1, 5) - sensitivities[0]
            # display(['Sensitivity of ' + str(acc_kalib[1]) + ' pm/g' + ' at ' + str(self.GainMark) + ' Hz'])
        else:
            acc_kalib.append(sensitivities[0] * 1000.0)
            # display(['Sensitivity of ' + str(acc_kalib[1]) + ' pm/g' + ' at ' + str(self.GainMark) + ' Hz'])
        # %% Calcualating flatness of sensitivity between edge-frequencies, these can be adjusted as desired
        flatness_edge_l = self.l_flatness  # Left flatness edge frequency
        flatness_edge_r = self.r_flatness  # Right flatness edge frequency

        acc_kalib.append(flatness_edge_l)
        acc_kalib.append(flatness_edge_r)
        acc_kalib.append(round(abs(fun.interp1_for_remco(FreqTransfer, 20 * np.log(abs(SmoothTransfer)),
                                            flatness_edge_l) - fun.interp1_for_remco(FreqTransfer,
                                            20 * np.log(abs(SmoothTransfer)), flatness_edge_r)), 1))

        # display(['Sensitivity flatness between ' + str(flatness_edge_l) + ' Hz and ' + str(flatness_edge_r) + ' Hz is: ' + str(acc_kalib[4])])

        acc_kalib.append(round(max(opt_sens_filtered), 3))
        acc_kalib.append(round(min(opt_sens_filtered), 4))
        acc_kalib.append(round(((max(opt_sens_filtered) - abs(min(opt_sens_filtered))) / max(opt_sens_filtered)) * 100, 4))
        # display(['Maximum acceleration = ' + str(acc_kalib[5]) + ' g and ' + 'minimum acceleration = ' + str(acc_kalib[6])])
        # display(['Difference in symmetry = ' + str(acc_kalib[7]) + '%'])
        # %% Make Phase Array and determine phase difference
        AngleSetFreq = self.AngleSetFreq
        phase_difference = np.unwrap(np.angle(Transfer)) * 180 / np.pi

        # Smoothing of the phase difference
        phase_difference_smooth = signal_filtfilt(B, A, phase_difference)

        phase_shift = fun.interp1_for_remco(FreqTransfer, phase_difference_smooth, AngleSetFreq)
        phase_difference_shifted = phase_difference_smooth - phase_shift
        # %% Time correction from phase data
        phase_mark = self.phase_mark
        phase_at_mark = fun.interp1_for_remco(FreqTransfer, phase_difference_shifted, phase_mark)
        TimeCorrection = phase_at_mark / 360 / phase_mark
        acc_kalib.append(TimeCorrection)

        acc_kalib.append(cw2)
        acc_kalib.append(offset)
        # display(['Calculated TimeCorrection is: ' + str(acc_kalib[8])])
        # Saving of time correction for further use
        if (self.Adjust_time_correction == 1) and Adjust_gain:
            if abs(TimeCorrection) > 0.001 / BodeSampFreq:
                # display(['Time correction used'])
                time_corrections[0] = time_corrections[0] + (1 / 0.9) * TimeCorrection
                # time_corrections[0] = 0
            else:
                pass
                # display(['TimeCorrection not used'])
        else:
            pass
            # display(['TimeCorrection not used'])
        # %% Save timecorrections and sensitivities
        os_chdir(self.Main_folder_path)
        # np.savetxt('time_corrections.csv', time_corrections)
        # np.savetxt('sensitivities.csv', sensitivities)
        # %% Plotting
        # Make_plots = 1
        yScaleBode = [-10, 10]
        yScalePhase = [-5, 5]
        x_tick = [10, 25, 50, 75, 100, 125, 150, 175, 200]

        TitleFontSize = 12
        LabelFontSize = 16
        BodeLineWidth = 3

        # optical_sensor_data = fun.calculateAC(-(DataOptRel[self.Opt_samp_freq:len(DataOptRel-1), 0] -
        #                                         DataOptRel[self.Opt_samp_freq:len(DataOptRel-1), 1]) +
        #                                       (round(np.mean(DataOptRel[100:200, 0]), 5) -
        #                                        round(np.mean(DataOptRel[100:200, 1]), 5)), Sensitivity_opt)
        # if make_plots:
            # plt.figure(num='Raw data')
            # plt.plot(TimeOpt, optical_sensor_data, label='Optical')
            # plt.plot(TimeRefShifted, reference_sensor_data, label='Reference')
            # plt.legend(prop={"size": 12})
            # plt.title('Shifted data', fontsize=TitleFontSize)
            # plt.ylabel('Acceleration [g]', fontsize=LabelFontSize)
            # plt.xlabel('Time[s]', fontsize=LabelFontSize)
            # plt.grid(which='both')
            # plt.minorticks_on()
            # plt.show()
            #
            # if self.Filter_on:
            #     plt.figure(num='Filtered data')
            #     plt.plot(TimeOpt, opt_sens_filtered, label='Optical')
            #     plt.plot(TimeRefShifted, ref_sens_filtered, label='Reference')
            #     plt.legend()
            #     plt.title('Filtered data', fontsize=TitleFontSize)
            #     plt.ylabel('Acceleration [g]', fontsize=LabelFontSize)
            #     plt.xlabel('Time[s]', fontsize=LabelFontSize)
            #     plt.grid(which='both')
            #     plt.minorticks_on()
            #     plt.show()

            # plt.figure(num='Resized filtered data')
            # plt.plot(TimeOptSensResized, OptSensResized, label='Optical')
            # plt.plot(TimeRefSensResized, RefSensResized, label='Reference')
            # plt.legend()
            # plt.title('Resampled and resized data of ' + self.ref_opt_name, fontsize=TitleFontSize)
            # plt.ylabel('Acceleration [g]', fontsize=LabelFontSize)
            # plt.xlabel('Time[s]', fontsize=LabelFontSize)
            # plt.grid(which='both')
            # plt.minorticks_on()
            # plt.show()

            # if self.Do_spectrum:
            #     plt.figure(num='Power spectrum')
            #     plt.plot(FreqOptPSD, 20 * np.log(abs(SmoothOptPSD)), label='Optical')
            #     plt.plot(FreqRefPSD, 20 * np.log(abs(SmoothRefPSD)), label='Reference')
            #     plt.legend()
            #     plt.title('Spectrum of ' + self.ref_opt_name, fontsize=TitleFontSize)
            #     plt.ylabel('Spectral Density [dB]', fontsize=LabelFontSize)
            #     plt.xlabel('Frequency [Hz]', fontsize=LabelFontSize)
            #     plt.grid(which='both')
            #     plt.minorticks_on()
            #     plt.xlim(5, 200)
            #     plt.show()

            # plt.figure(num='Bode analysis')
            # plt.plot(FreqTransfer, 20 * np.log(abs(SmoothTransfer)), linewidth=BodeLineWidth)
            # plt.title('Bode Analysis of ' + self.ref_opt_name, fontsize=TitleFontSize)
            # plt.ylim(-10, 10)
            # plt.xlabel('Frequency [Hz]', fontsize=LabelFontSize)
            # plt.ylabel('Gain [dB]', fontsize=LabelFontSize)
            # plt.xlim(self.xScaleTransfer)
            # plt.grid(which='both')
            # plt.minorticks_on()
            # plt.show()
            #
            # fig, axs = plt.subplots(2, num='Frequency response')
            # axs[0].plot(FreqTransfer, 20 * np.log(abs(SmoothTransfer)), linewidth=BodeLineWidth)
            # axs[0].set_title('Bode')
            # axs[0].set_xticks(x_tick)
            # axs[0].set_xlim(self.xScale)
            # axs[0].set_ylim(yScaleBode)
            # axs[0].set_xlabel('Frequency [Hz]', fontsize=LabelFontSize)
            # axs[0].set_ylabel('Gain [dB]', fontsize=LabelFontSize)
            # axs[0].grid(which='both')
            # axs[0].minorticks_on()
            # axs[1].plot(FreqTransfer, phase_difference_shifted, linewidth=BodeLineWidth)
            # axs[1].set_title('Phase')
            # axs[1].set_xticks(x_tick)
            # axs[1].set_xlim(self.xScale)
            # axs[1].set_ylim(yScalePhase)
            # # axs[1].set_ylim(-150, 150)
            # axs[1].set_xlabel('Frequency [Hz]', fontsize=LabelFontSize)
            # axs[1].set_ylabel('Phase [°]', fontsize=LabelFontSize)
            # axs[1].grid(which='both')
            # axs[1].minorticks_on()
            # plt.xscale('log')
            # plt.tight_layout()
            # plt.show()

        return (acc_kalib, TimeOptSensResized, OptSensResized, TimeRefSensResized, RefSensResized,
                FreqOptPSD, (20 * np.log(abs(SmoothOptPSD))), FreqRefPSD, (20 * np.log(abs(SmoothRefPSD))))
