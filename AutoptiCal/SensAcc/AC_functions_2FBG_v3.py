# -*- coding: utf-8 -*-
"""
Created on Thu Mar 31 13:38:29 2022

@author: ErayMyumyun
"""
from fnmatch import fnmatch

import numpy as np
from pandas import read_csv as pd_read_csv, DataFrame as pd_DataFrame
from scipy import fft
from math import log2 as math_log2, ceil as math_ceil
from os.path import isfile as os_path_isfile, join as path_join
from os import walk as os_walk

# def mov_avg(y, x):
#     '''
#     Computes the moving average of a single array of data.
#
#     Returns the moving average of an array of elements. The moving average is
#     calculated by making a one-dimentional box with a length of x and taking
#     the average of all the values within the box. After the calculated value is
#     saved, the box moves forward 1 element.
#
#     Parameters
#     ----------
#     y : (N, M) array_like
#         Input array, can be one or two dimentional
#     x : int
#         Gives the size of the box
#
#     Returm
#     ------
#     out : (O, M) array_like
#         Returns the data with a moving average. The output array is the same as
#         input array except the length of the output array is shorter. The data
#         points are shortend by a total amount of x, x/2 at the start of the
#         array and x/2 at the end of the array.
#     '''
#     box = np.ones(x)/x
#     if len(y.shape) == 1:
#         print('One dimentional array detected.')
#         y_smooth = np.convolve(y,box,mode='same')
#         out = y_smooth[int(x/2):-int(x/2)]
#         return out
#     if len(y.shape) == 2:
#         print('Two dimentional array detected.')
#         out = np.empty(shape=(len(y) - x, y.shape[1]))
#         for i in range(0, y.shape[1]):
#             y_smooth = np.convolve(y[0:, i], box, mode='same')
#             y_new = y_smooth[int(x/2):-int(x/2)]
#             out[0:, i] = y_new
#         return out

# def convert_full_time(time_full):
#     '''
#     Converts full timestamp to (YYYY-MM-DD HH:MM:SS.MS) to seconds.
#
#     Returns a list of time values in seconds. The full timestamp can have / or
#     - as seperators.
#
#     Parameters
#     ----------
#     time_full : (N,) array_like
#         Input array, one dimentional array.
#
#     Return
#     ------
#     time_sec : (N,) array_like
#         Returns a one dimentional numpy array.
#     '''
#     # Change the timestamp from 'YYYY-MM-DD HH:MM:SS.MS' to 'YYYY:MM:DD:HH:MM:SS:MS'
#     for j in range(0, len(time_full)):
#         time_full[j,0] = re.sub('[-/ .]',':', time_full[j,0])
#         time_full[j,0] = time_full[j,0] + str(0)
#
#     # Converts the timestamp to seconds
#     time_sec = []
#     for j in range(0, len(time_full)):
#         tm = time_full[j,0].split(':')
#         dt = datetime.datetime(int(tm[2]), int(tm[1]), int(tm[0]), int(tm[3]) ,int(tm[4]) ,int(tm[5]), int(tm[6]))
#         seconds = time.mktime(dt.timetuple())
#         seconds += (dt.microsecond/1000000.0)
#         time_sec.append(seconds)
#     time_sec = np.array(time_sec)
#     return time_sec

def detect_txt_files(path_folder):
    '''
    Detects all txt files in a given folder

    Parameters
    ----------
    path_folder : str, path object or file-like object
        Any valid string path is acceptable. The string could be a URL. Valid
        URL schemes include http, ftp, s3, gs, and file. For file URLs, a host
        is expected.

    Return
    ------
    fullnames : list
        List with the full names of the txt files. Fullname consists of the
        path and filename.
    '''
    fullnames = []
    for path,dirs,files in os_walk(path_folder):
        for file in files:
            if fnmatch(file,'*.txt'):
                fullname = path_join(path,file)
                if fullname.endswith('.txt'):
                    fullnames.append(fullname)
    return fullnames

# def read_Enlight_Data(txt_file):
#     '''
#     Reads in the data of the Enlight.
#
#     Returns an array of data saved with the Enlight software. Optionally, the
#     header can also be returned. If the header is enabled, returned value is an
#     tuple with size 2.
#
#     Parameters
#     ----------
#     txt_file : str, path object or file-like object
#         Any valid string path is acceptable. The string could be a URL. Valid
#         URL schemes include http, ftp, s3, gs, and file. For file URLs, a host
#         is expected.
#
#     Return
#     ------
#     data : numpy array
#         An array of the loaded data.
#     header : numpy array, optional
#         Gives the data and header of the loaded data. The returned value is a
#         tuple with size 2.
#     '''
#     # Get first line of txt file. This line gives how many rows need to be skipped before the actual data is reached
#     with open(txt_file) as f:
#         firstlinestr = f.readline().rstrip()
#         f.close()
#
#     firstline = int(firstlinestr)                                              # Make int from str
#     firstline = firstline                                                      # Select header as well
#     # Load in txt file and skip lines with text
#     text = pd.read_csv(txt_file, skiprows=firstline, decimal=',', delimiter="\t")
#     data = pd.DataFrame.to_numpy(text)                                         # Convert pandas DataFrame to numpy array
#
#     return data

def read_txt_file(txt_file, skiprows, decimal=','):
    '''
    Reads in the data from txt or csv file.

    Returns an array of data. The header is disabled.

    Parameters
    ----------
    txt_file : str, path object or file-like object
        Any valid string path is acceptable. The string could be a URL. Valid
        URL schemes include http, ftp, s3, gs, and file. For file URLs, a host
        is expected.
    skiprows : int
        Give how many rows to skip before real data is met

    Return
    ------
    data : numpy array
        An array of the loaded data.
    '''
    # Load in txt file and skip lines with text
    text = pd_read_csv(txt_file, skiprows = skiprows, decimal = decimal, delimiter = "\t", header = None)
    data = pd_DataFrame.to_numpy(text)                                         # Convert pandas DataFrame to numpy array
    return data

def calculateAC(data_wavelength, sensitivity_opt):
    '''
    Converts wavelengths to acceleration by dividing data with sensitivity.

    Returns an array of data.

    Parameters
    ----------
    data_wavelength : (N,) array_like
        Input array, one dimentional array.
    sensitivity_opt : float
        The sensitivity of the sensor

    Return
    ------
    DataAC : (N,) array_like
        An array of the acceleration
    '''
    # Calculate acceleration of data by dividing data with sensitivity
    DataAC = data_wavelength/sensitivity_opt
    return DataAC

def resample_by_interpolation(signal, input_fs, output_fs):
    # Resample input signal with input frequency to output frequency
    scale = output_fs / input_fs
    # Calculate new length of sample
    n = round(len(signal) * scale)

    # Use linear interpolation
    # endpoint keyword means than linspace doesn't go all the way to 1.0
    # If it did, there are some off-by-one errors
    # e.g. scale=2.0, [1,2,3] should go to [1,1.5,2,2.5,3,3]
    # but with endpoint=True, we get [1,1.4,1.8,2.2,2.6,3]
    # Both are OK, but since resampling will often involve
    # exact ratios (i.e. for 44100 to 22050 or vice versa)
    # using endpoint=False gets less noise in the resampled sound
    resampled_signal = np.interp(np.linspace(0.0, 1.0,n,endpoint=False),  # where to interpret
        np.linspace(0.0, 1.0, len(signal), endpoint=False),  # known positions
        signal,  # known data points
    )
    return resampled_signal

def SignalResize(Signal1,Signal2,SampleDiff):

    # This function cuts data signals such that they are the same length and
    # are corrected for a time shift.

    # if SampleDiff is positive then functions cuts of data from signal1
    # or (synonimously) assumes signal1 started earlier
    # and if SammpleDiff is negfative it cuts from signal2

    if SampleDiff > 0:
        Signal1Resized=Signal1[int(SampleDiff-1):-1]
        Signal2Resized=Signal2
        if len(Signal1Resized) > len(Signal2Resized):
            Signal1Resized=Signal1Resized[0:len(Signal2Resized)]
        else:
            Signal2Resized=Signal2Resized[0:len(Signal1Resized)]
    else:
        if SampleDiff < 0:
            Signal1Resized=Signal1
            Signal2Resized=Signal2[int(-SampleDiff-1):-1]
            if len(Signal1Resized) > len(Signal2Resized):
                Signal1Resized=Signal1Resized[0:len(Signal2Resized)]
            else:
                Signal2Resized=Signal2Resized[0:len(Signal1Resized)]
        else:
            if SampleDiff == 0:
                if len(Signal1) > len(Signal2):
                    Signal1Resized=Signal1[0:len(Signal2)]
                    Signal2Resized=Signal2
                else:
                    Signal1Resized=Signal1
                    Signal2Resized=Signal2[0:len(Signal1)]

    return Signal1Resized,Signal2Resized

def FourierAnalisis(SignalIn,SignalOut,AqFreq):
    #Performing of fourier analysis on signals and returns transfer function and correspondig frequencies
    NFFT = 2**math_ceil(math_log2(abs(len(SignalOut))))
    SpectrumSignalIn = fft.fft(SignalIn,NFFT)/NFFT
    SpectrumSignalOut = fft.fft(SignalOut,NFFT)/NFFT

    SInOut= np.conj(SpectrumSignalIn)*SpectrumSignalOut
    SInIn = np.conj(SpectrumSignalIn)*SpectrumSignalIn
    Transfer = SInOut/SInIn
    x = int(len(Transfer)/2)
    Transfer = Transfer[0:x]
    FreqTransfer = AqFreq/2*np.linspace(0,1,num=int((NFFT/2)))
    return Transfer,FreqTransfer

def interp1_for_remco(x,y,x_prime):
    #Finds y_prime at location x_prime with linear interpolation of two
    #points in y.

    x_l_index = np.where(x < x_prime)
    x_l_index = x_l_index[-1][-1]
    x_r_index = np.where(x > x_prime)
    x_r_index = x_r_index[0][0]

    y_l = y[x_l_index]
    x_l = x[x_l_index]
    y_r = y[x_r_index]
    x_r = x[x_r_index]

    y_prime = y_l + ((x_prime-x_r)/(x_r_index-x_l)*(y_r-y_l))
    return y_prime

# def read_Enlight_Data_AC(txt_file):
#     # Reading of wavelength data from MicronOptics interrogator output
#     # Tab-delimited text file with headers
#     # Get first line of txt file. This line gives how many rows need to be skipped before the actual data is reached
#     if os.path.isfile(txt_file) is True:
#         with open(txt_file) as f:
#             firstlinestr = f.readline().rstrip()
#             f.close()
#         firstline = int(firstlinestr)                                              # Make int from str
#
#         File = open(txt_file, 'r',).readlines()
#         Data1 = []
#         Data2 = []
#         for line in File[firstline:]:
#             l = line.strip().split('\t')
#             Data1.append(float(l[-2].replace(',','.')))
#             Data2.append(float(l[-1].replace(',','.')))
#
#         Data = np.full([len(File) - firstline,2], None)
#         for i in range(len(File) - firstline):
#             Data[i,0] = Data1[i]
#             Data[i,1] = Data2[i]
#
#     else:
#         Data = 0
#
#     return Data

def read_txt_file_AC(txt_file, skiprows):
    # Reading of wavelength data from MicronOptics interrogator output
    # Tab-delimited text file with headers
    # Get first line of txt file. This line gives how many rows need to be skipped before the actual data is reached
    if os_path_isfile(txt_file) is True:
        File = open(txt_file, 'r',).readlines()
        Data1 = []
        Data2 = []
        for line in File[skiprows:]:
            l = line.strip().split('\t')
            Data1.append(float(l[-2].replace(',','.')))
            Data2.append(float(l[-1].replace(',','.')))

        Data = np.full([len(File) - skiprows,2], None)
        for i in range(len(File) - skiprows):
            Data[i,0] = Data1[i]
            Data[i,1] = Data2[i]

    else:
        Data = 0

    return Data