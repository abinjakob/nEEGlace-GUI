# -*- coding: utf-8 -*-

# libraries
import time
import os
import signal
import math
# interface
import tkinter 
import customtkinter
# subprocess
import subprocess
import threading 
# for ssh connection with Bela
import paramiko
# lsl
import matplotlib.pyplot as plt
from pylsl import StreamInlet, StreamInfo, resolve_stream
from pathlib import Path

# import modules
from nEEGlace.belaconnect import checkBelaStatus, getBelaConfig, dumpBelaConfig
from nEEGlace.connectLSL import connectstreams
from nEEGlace.streamPlotter import plotEEG
from nEEGlace.advertiseLSL import LSLestablisher, LSLkiller


def main():
    
    # SETTINGS ---------------------------------------------------

    # -- EEG AMPLIFIER PARAMS
    # enter device name  
    deviceName = 'Explore_DAAH' 
    # enter EEG channels in the stream 
    nbchans = 18
    # channel used for sound triggers
    triggerChan = 19


    # -- SOUND TRIGGERS PARAMS
    # threshold for sound detection
    soundThresh = 200


    # -- OTHERS
    # common outputs of push2lsl
    errstr1   = 'not recognised as an internal or external command'
    errstr2   = 'DeviceNotFoundError'
    successtr = 'Device info packet has been received. Connection has been established. Streaming...'

    # ----------------------------------------------------------
    
    
    # --- app frames ---
    # open the config file and fetch data
    project_root = Path(os.getcwd())
    configfile = project_root / 'config' / 'nEEGlaceConfigfile.txt'
    ani = None
    
    # channel index of the sound trigger 
    tidx = triggerChan-1
    # list of EEG chans
    eegchans = list(range(nbchans))
    
    if tidx in eegchans:
        # remove sound trigger channel from EEG channels 
        eegchans = [x for x in eegchans if x != tidx]
    else:
        # adjust total channels 
        nbchans = nbchans +1
    
    
    
    
    
    
    
    # function to read text file
    def readConfig():
        with open(configfile, 'r') as f:
            lines = f.readlines()
        return lines
    # function to fetch data from config file
    def fetchConfig():   
        global bela_micgain, bela_thresh, bela_record, bela_recorddur, stream_erpavg, stream_tmin, stream_tmax
        # read lines from config file
        configlines = readConfig()
        # fetching data
        bela_micgain   = int(configlines[0])
        bela_thresh    = float(configlines[1])
        bela_record    = int(configlines[2])
        bela_recorddur = int(configlines[3])
        stream_erpavg  = int(configlines[4])
        stream_tmin    = float(configlines[5])
        stream_tmax    = float(configlines[6])   
        return bela_micgain, bela_thresh, bela_record, bela_recorddur, stream_erpavg, stream_tmin, stream_tmax
    
    # function to dump data to config file
    def dumpConfig():
        with open(configfile, 'w') as f:
            f.writelines(f'{bela_micgain}\n')
            f.writelines(f'{bela_thresh}\n')
            f.writelines(f'{bela_record}\n')
            f.writelines(f'{bela_recorddur}\n')
            f.writelines(f'{stream_erpavg}\n')
            f.writelines(f'{stream_tmin}\n')
            f.writelines(f'{stream_tmax}\n')
    
    # function to read and update from the Bela config file
    def updateConfig():
        global belastatus
        configlines = readConfig()
        belavalues, belastatus = getBelaConfig()
        if belastatus:    
            configlines[0] = f'{belavalues[1]}\n'
            configlines[1] = f'{belavalues[0]}\n'
            configlines[2] = f'{belavalues[2]}\n'
            configlines[3] = f'{belavalues[3]}\n'
            with open(configfile, 'w') as f:
                f.writelines(configlines)
            
    
    # function to dump config settings to Bela board 
    def updateBela():
        configlines = readConfig()
        values = [configlines[0], configlines[1], configlines[2], configlines[3]]
        time.sleep(1)
        writestatus = dumpBelaConfig(values)
        return writestatus
    
    
    # system settings 
    customtkinter.set_appearance_mode('dark')
    customtkinter.set_default_color_theme('blue')
    
    # app frame
    app = customtkinter.CTk()
    app.geometry('720x480')
    
    # function to handle closing the window
    def on_closingwindow(): 
        LSLkiller(deviceName)
        app.quit()
        app.destroy()
    
    # setting the protocol to handle window close
    app.protocol("WM_DELETE_WINDOW", on_closingwindow)
    
    # font styles 
    H1 = ('Arial', 24, 'bold')
    H2 = ('Arial', 20, 'bold')
    H3 = ('Arial', 16, 'bold')
    B1 = ('Arial', 14)
    B2 = ('Arial', 12)
    B3 = ('Arial', 10)
    
    # color palette 
    UItextbox = {'active': {'boxbg': '#343638', 'boxborder': '#565b5e', 'boxfont': '#ffffff'},
                      'deactive': {'boxbg': '#2b2b2b', 'boxborder': '#343638', 'boxfont': '#5f5f5f'}}
    UIfont = {'normal': '#ffffff', 'notes': '#5f5f5f','deactive': '#5f5f5f', 'error': '#f34444', 'success': '#2cd756'}
    
    # configure grid layout 
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)
    
    
        
    
    
    # --- app frames ---
    
    # main frame 
    mainFrame= customtkinter.CTkFrame(app)
    mainFrame.grid(row=0, column=0, sticky='nsew')
    
    # troubleshoot frame 1
    troubleshootFrame1= customtkinter.CTkFrame(app)
    troubleshootFrame1.grid(row=0, column=0, sticky='nsew')
    troubleshootFrame1.grid_forget()
    
    # troubleshoot frame 2
    troubleshootFrame2= customtkinter.CTkFrame(app)
    troubleshootFrame2.grid(row=0, column=0, sticky='nsew')
    troubleshootFrame2.grid_forget()
    
    # troubleshoot frame 3
    troubleshootFrame3= customtkinter.CTkFrame(app)
    troubleshootFrame3.grid(row=0, column=0, sticky='nsew')
    troubleshootFrame3.grid_forget()
    
    # test audio frame
    testaudioframe = customtkinter.CTkFrame(app)
    testaudioframe.grid(row=0, column=0, sticky='nsew')
    testaudioframe.grid_forget()
    
    # configure frame
    configFrameMain = customtkinter.CTkFrame(app)
    configFrameMain.grid(row=0, column=0, sticky='nsew')
    configFrameMain.grid_forget()
    
    # streamerConnect Frame
    streamerFrameLoad = customtkinter.CTkFrame(app)
    streamerFrameLoad.grid(row=0, column=0, sticky='nsew')
    streamerFrameLoad.grid_forget()
    
    # streamerFrame
    streamerFrameMain = customtkinter.CTkFrame(app)
    streamerFrameMain.grid(row=0, column=0, sticky='nsew')
    streamerFrameMain.grid_forget()
    
    # impedanceFrame
    impedanceFrame = customtkinter.CTkFrame(app)
    impedanceFrame.grid(row=0, column=0, sticky='nsew')
    impedanceFrame.grid_forget()
    
    # configure grid layout for frames (add all frames here)
    for frame in (mainFrame, troubleshootFrame1, troubleshootFrame2, troubleshootFrame3, testaudioframe, configFrameMain, streamerFrameMain, streamerFrameLoad, impedanceFrame):
        frame.grid_rowconfigure(9, weight=1)
        for i in range(10):
            frame.grid_columnconfigure(i, weight=1)
    
    
    
    
    # --- main frame UI ---
    
    # function to connect to stream
    def connect2Stream():
        global streamStatus
        # run the LSLestablisher module
        streamStatus = LSLestablisher(deviceName)
    
    # button functions
    def on_troubleshoot():
        mainFrame.grid_forget()
        troubleshootFrame1.grid(sticky='nsew')
        
        
        
        
        
   
# --------------->TEMP CODE<-----------------------   
    # -- UNCOMMENT ORIGINAL -- 
    # def on_config(): 
    #     mainFrame.grid_forget()
    #     configFrameMain.grid(sticky='nsew')
    #     updateConfig()
    
    def on_config(): 
        global electrode_items
        mainFrame.grid_forget()
        impedanceFrame.grid(sticky='nsew')
        electrode_items = drawElectrodes(left_positions) + drawElectrodes(right_positions)
# --------------------------------------------------
    
    
        
        
        
    def on_start():
        global inlet, streaminfo, sfreq, nchan
        
        # move to loading screen
        mainFrame.grid_forget()
        streamerFrameLoad.grid(sticky='nsew')
        
        # start a seperate thread for LSL advertising
        thread4LSL = threading.Thread(target= connect2Stream)
        thread4LSL.start()
        # continuously checking streamStatus
        checkThread4LSL(thread4LSL)
    
    # function to continuously check streamStatus from the thread
    stopCheck = False
    def checkThread4LSL(thread4LSL):
        global streams, inlet, srate, nbchans, stopCheck
        stopCheck = False
        # checks every 100ms if thread is complete
        if thread4LSL.is_alive():
            if not stopCheck: 
                streamerFrameLoad.after(300, lambda: checkThread4LSL(thread4LSL))
        elif streamStatus == 1:
            # run connectStream module
            inlet, streaminfo = connectstreams()
            
            # check if connected 
            if not inlet:
                print('Error: Cant connect to stream')
                srate = 0
                nbchans = 0
            else:
                configdata = fetchConfig()
                srate = streaminfo.nominal_srate()
                # nbchans  = streaminfo.channel_count()
                print(f'Sampling Rate: {srate}')
                
                # updating the variables in the streamer main frame
                strM_sfreqans.configure(text= int(streaminfo.nominal_srate()))
                strM_nchanans.configure(text= streaminfo.channel_count())
                strM_trgchanans.configure(text= triggerChan)
                if configdata[2] == 0:
                    recordAns = 'OFF'
                    recordansClr = UIfont['error']
                elif configdata[2] == 1:
                    recordAns = 'ON'
                    recordansClr = UIfont['success']
                strM_recordans.configure(text= recordAns, text_color= recordansClr)
                streamerFrameLoad.grid_forget()
                streamerFrameMain.grid(sticky='nsew')
        else:
            # throw an error in GUI
            strL_body.configure(text = 'Error: Cannot advertise LSL. Please try again.', text_color=UIfont['error'])
            strL_bar.stop()
            strL_bar.grid_forget()
            # move back to main screen after a short while
            streamerFrameLoad.after(2000, lambda: (streamerFrameLoad.grid_forget(), mainFrame.grid(sticky='nsew')))
                
    
    # title 
    title = customtkinter.CTkLabel(mainFrame, text= 'Welcome to nEEGlace', font=H1)
    title.grid(row=0, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (40,0))
    # body text '
    bodystr = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor\nincididunt ut labore et dolore magna aliqua.'
    body = customtkinter.CTkLabel(mainFrame, text= bodystr, font=B2, text_color='#979797', justify= 'left')
    body.grid(row=2, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (10,0))
    
    # troubleshoot button
    BTtroubleshoot = customtkinter.CTkButton(mainFrame, text= 'Troubleshoot', fg_color='#5b5b5b', text_color='#b6b6b6', hover_color='#4f4f4f',
                                             command= on_troubleshoot)
    BTtroubleshoot.grid(row=9, column=0, sticky='sw', padx= (40,0), pady= (0,40))
    # setup buttons
    BTconfig = customtkinter.CTkButton(mainFrame, text= 'Configure nEEGlace', fg_color='#ffffff', text_color='#000000', hover_color='#979797',
                                       command= on_config)
    BTconfig.grid(row=9, column=1, sticky='sw', padx= (0,10), pady= (0,40))
    # start recording button
    BTstart = customtkinter.CTkButton(mainFrame, text= 'Start Streaming', 
                                      command= on_start)
    BTstart.grid(row=9, column=9, sticky='se', padx= (10,40), pady= (0,40))
    
    
    
    
    # --- troubleshoot frame1 UI ---
    # checking if the device is on
    
    # button functions
    def on_t1back():
        troubleshootFrame1.grid_forget()
        mainFrame.grid(sticky='nsew')
        
    def on_t1next():
        if t1_Q1radioInput.get()==0:
            t1_Q1label.configure(text= 'Cant turn on nEEGlace! Please try again after charging the battery', text_color='#f34444')
        else:
            t1_Q1label.configure(text= '', text_color='#2cd756')
            troubleshootFrame1.grid_forget()
            troubleshootFrame2.grid(sticky='nsew')
            
        
    # title 
    t1_title =  customtkinter.CTkLabel(troubleshootFrame1, text= 'Setup nEEGlace', font=H2)
    t1_title.grid(row=0, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (40,0))
    # device status
    t1_devicestat = customtkinter.CTkLabel(troubleshootFrame1, text= 'Device Status:', font=B2, text_color='#979797', justify= 'left')
    t1_devicestat.grid(row=1, column=0, sticky='w', padx= (40,0), pady= (2,0))
    t1_devicestatans = customtkinter.CTkLabel(troubleshootFrame1, text= '-', font=B2, text_color='#979797', justify= 'left')
    t1_devicestatans.grid(row=1, column=0, sticky='w', padx= (125,0), pady= (2,0))
    t1_ampstat = customtkinter.CTkLabel(troubleshootFrame1, text= 'Amplifier Status:', font=B2, text_color='#979797', justify= 'left')
    t1_ampstat.grid(row=1, column=1, sticky='w', padx= (0,0), pady= (2,0))
    t1_ampstatans = customtkinter.CTkLabel(troubleshootFrame1, text= '-', font=B2, text_color='#979797', justify= 'left')
    t1_ampstatans.grid(row=1, column=1, sticky='w', padx= (100,0), pady= (2,0))
    # body font
    t1_body1 = customtkinter.CTkLabel(troubleshootFrame1, text= 'Step 1', font=H3, justify= 'left')
    t1_body1.grid(row=2, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (0,0))
    t1_bodystr = 'Turn on nEEglace by flipping the switch situated on the right\nside of the device'
    t1_body2 = customtkinter.CTkLabel(troubleshootFrame1, text= t1_bodystr, font=B1, justify= 'left')
    t1_body2.grid(row=2, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (60,0))
    
    # ask if the device is on
    t1_Q1str = 'Can you see a red light next to the switch?'
    t1_Q1 = customtkinter.CTkLabel(troubleshootFrame1, text= t1_Q1str, font=B1, text_color='#979797', justify= 'left')
    t1_Q1.grid(row=3, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (0,0))
    # radio button int variable for input
    t1_Q1radioInput = tkinter.IntVar(value=0)
    t1_Q1radio1 = customtkinter.CTkRadioButton(troubleshootFrame1, text= 'Yes', variable=t1_Q1radioInput, value= 1)
    t1_Q1radio1.grid(row=3, column=0, sticky='w', padx=(40, 0), pady=(60, 0))
    t1_Q1radio2 = customtkinter.CTkRadioButton(troubleshootFrame1, text= 'No', variable=t1_Q1radioInput, value= 0)
    t1_Q1radio2.grid(row=4, column=0, sticky='w', padx=(40, 0), pady=(8, 0))
    
    # error label
    t1_Q1label = customtkinter.CTkLabel(troubleshootFrame1, text= '', font=B2, justify= 'left')
    t1_Q1label.grid(row=9, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (0,10))
    
    # back button
    t1_BTback2main = customtkinter.CTkButton(troubleshootFrame1, text= 'Back to Main Menu', fg_color='#5b5b5b', text_color='#b6b6b6', hover_color='#4f4f4f', 
                                     command= on_t1back)
    t1_BTback2main.grid(row=9, column=0, sticky='sw', padx= (40,0), pady= (0,40))
    # next button
    t1_BTnext = customtkinter.CTkButton(troubleshootFrame1, text= 'Next  >>', 
                                     command= on_t1next)
    t1_BTnext.grid(row=9, column=9, sticky='se', padx= (10,40), pady= (0,40))
    
    
    
    
    # --- troubleshoot frame2 UI ---
    # checking the status of the Mentalab amp
    
    # function to connect to stream
    def t2connectStream():
        global isConnected, streamStatus
        # initialising glob variables 
        isConnected  = False
        streamStatus = 0
        streamStatus = LSLestablisher(deviceName)
        
    
    # button functions
    def on_t2back():
        troubleshootFrame2.grid_forget()
        mainFrame.grid(sticky='nsew')
    def on_t2prev():
        troubleshootFrame2.grid_forget()
        troubleshootFrame1.grid(sticky='nsew')
    def on_t2next():
        if t2_Q1radioInput.get()==1:
            t2_Q1label.configure(text= 'nEEGlace is in Offline mode! Cant stream data.', text_color='#f34444')
        elif t2_Q1radioInput.get()==2:
            t2_Q1label.configure(text= 'Amplifier is starting up. Wait for sometime until it turns blue.', text_color='#f34444')
        elif t2_Q1radioInput.get()==3:
            t2_Q1label.configure(text= 'Amplifier has low battery! Need to charge the Amplifier.', text_color='#f34444')       
        else:
            t2_ampstatans.configure(text= 'Bluetooth ON', text_color='#569cff')
            t2_Q1label.configure(text= 'Connecting to LSL network', text_color='#ffffff')
            # disable button
            t2_BTback2main.configure(state='disabled')
            t2_BTprev.configure(state='disabled')
            t2_BTnext.configure(state='disabled')
            # disable options
            t2_Q1radio1.configure(state='disabled')
            t2_Q1radio2.configure(state='disabled')
            t2_Q1radio3.configure(state='disabled')
            t2_Q1radio4.configure(state='disabled')
            
            # run progressbar
            t2_bar.grid(row=9, column=1, sticky='w', padx= (20,0), pady= (0,60))
            t2_bar.start()
            
            # attempt connection (starting in different thread to avoid UI being frozen)
            connectionThread = threading.Thread(target= t2connectStream)
            connectionThread.start()
            # continuously checking streamStatus
            checkThread(connectionThread)
    
    # function to continuously check streamStatus from the thread
    def checkThread(connectionThread):
        global inlet, srate, nbchans, stopCheck
        # checks every 100ms if thread is complete
        if connectionThread.is_alive():
            if not stopCheck:    
                troubleshootFrame2.after(300, lambda: checkThread(connectionThread))
        elif streamStatus == 1:
            try:
                inlet, streaminfo = connectstreams()
                if not inlet:
                    print('No inlet found')
                else:           
                    srate   = streaminfo.nominal_srate()
                    # nbchans = streaminfo.channel_count()
                    print('LSL stream connected')
                    t2_bar.stop()
                    t2_bar.grid_forget()
                    t2_Q1label.configure(text= 'Connected')
                    troubleshootFrame2.grid_forget()
                    troubleshootFrame3.grid(sticky='nsew')
                    stopCheck = True
            except Exception as e:
                print('Unable to connect to LSL stream')                     
        # if complete
        else:
            # check connection status
            if streamStatus == 2:
                t2_bar.stop()
                t2_bar.grid_forget()
                t2_Q1label.configure(text= 'Error: ExplorePy is not installed', text_color='#f34444')
            elif streamStatus == 3:
                t2_bar.stop()
                t2_bar.grid_forget()
                t2_Q1label.configure(text= 'Error: Restart and try again. Also kill the explorepy subprocess from Windows Task Manager if exist', text_color='#f34444')    
            elif streamStatus == 4:
                t2_bar.stop()
                t2_bar.grid_forget()
                t2_Q1label.configure(text= 'Error: Unable to connect to nEEGlace. Restart and try again.', text_color='#f34444')
            
                
    
    # title 
    t2_title =  customtkinter.CTkLabel(troubleshootFrame2, text= 'Troubleshoot nEEGlace', font=H2)
    t2_title.grid(row=0, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (40,0))
    # device status
    t2_devicestat = customtkinter.CTkLabel(troubleshootFrame2, text= 'Device Status:', font=B2, text_color='#979797', justify= 'left')
    t2_devicestat.grid(row=1, column=0, sticky='w', padx= (40,0), pady= (2,0))
    t2_devicestatans = customtkinter.CTkLabel(troubleshootFrame2, text= 'ON', font=B2, text_color='#2cd756', justify= 'left')
    t2_devicestatans.grid(row=1, column=0, sticky='w', padx= (125,0), pady= (2,0))
    t2_ampstat = customtkinter.CTkLabel(troubleshootFrame2, text= 'Amplifier Status:', font=B2, text_color='#979797', justify= 'left')
    t2_ampstat.grid(row=1, column=1, sticky='w', padx= (0,0), pady= (2,0))
    t2_ampstatans = customtkinter.CTkLabel(troubleshootFrame2, text= '-', font=B2, text_color='#979797', justify= 'left')
    t2_ampstatans.grid(row=1, column=1, sticky='w', padx= (100,0), pady= (2,0))
    # body font
    t2_body1 = customtkinter.CTkLabel(troubleshootFrame2, text= 'Step 2', font=H3, justify= 'left')
    t2_body1.grid(row=2, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (0,0))
    t2_bodystr = 'Please turn on the Amplifier by pressing the button on the top\nleft of the nEEGlace'
    t2_body2 = customtkinter.CTkLabel(troubleshootFrame2, text= t2_bodystr, font=B1, justify= 'left')
    t2_body2.grid(row=2, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (60,0))
    
    # ask if the device is on
    t2_Q1str = 'What light do you see on the amp?'
    t2_Q1 = customtkinter.CTkLabel(troubleshootFrame2, text= t2_Q1str, font=B1, text_color='#979797', justify= 'left')
    t2_Q1.grid(row=3, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (0,0))
    # radio button int variable for input
    t2_Q1radioInput = tkinter.IntVar(value=0)
    t2_Q1radio1 = customtkinter.CTkRadioButton(troubleshootFrame2, text= 'Blinking Blue', variable=t2_Q1radioInput, value= 0)
    t2_Q1radio1.grid(row=3, column=0, sticky='w', padx=(40, 0), pady=(60, 0))
    t2_Q1radio2 = customtkinter.CTkRadioButton(troubleshootFrame2, text= 'Blinking Green', variable=t2_Q1radioInput, value= 1)
    t2_Q1radio2.grid(row=4, column=0, sticky='w', padx=(40, 0), pady=(8, 0))
    t2_Q1radio3 = customtkinter.CTkRadioButton(troubleshootFrame2, text= 'Blinking Pink', variable=t2_Q1radioInput, value= 2)
    t2_Q1radio3.grid(row=5, column=0, sticky='w', padx=(40, 0), pady=(8, 0))
    t2_Q1radio4 = customtkinter.CTkRadioButton(troubleshootFrame2, text= 'Blinking Red & Turned off', variable=t2_Q1radioInput, value= 3)
    t2_Q1radio4.grid(row=6, column=0, columnspan= 2, sticky='w', padx=(40, 0), pady=(8, 0))
    
    # error label
    t2_Q1label = customtkinter.CTkLabel(troubleshootFrame2, text= '', font=B2, justify= 'left')
    t2_Q1label.grid(row=9, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (0,60))
    t2_bar = customtkinter.CTkProgressBar(troubleshootFrame2, progress_color= '#ffffff', height= 2, corner_radius=2)
    
    # back button
    t2_BTback2main = customtkinter.CTkButton(troubleshootFrame2, text= 'Back to Main Menu', fg_color='#5b5b5b', text_color='#b6b6b6', hover_color='#4f4f4f', 
                                     command= on_t2back)
    t2_BTback2main.grid(row=9, column=0, sticky='sw', padx= (40,0), pady= (0,40))
    # previous button 
    t2_BTprev = customtkinter.CTkButton(troubleshootFrame2, text= '<<  Prev', fg_color='#5b5b5b', text_color='#b6b6b6', hover_color='#4f4f4f', 
                                     command= on_t2prev)
    t2_BTprev.grid(row=9, column=9, sticky='se', padx= (0,190), pady= (0,40))
    # next button
    t2_BTnext = customtkinter.CTkButton(troubleshootFrame2, text= 'Next  >>',
                                        command= on_t2next)
    t2_BTnext.grid(row=9, column=9, sticky='se', padx= (10,40), pady= (0,40))
    
    
    
    
    # --- troubleshoot frame3 UI ---
    def detectSound():
        global sample
        sample = None
        # pull sample
        timestamp, sample = inlet[0].pullchunk()
        if sample is None or len(sample) == 0:
            return False 
        else:
            # check if trigger present 
            for s in sample:
                if s[tidx]> soundThresh:
                    print('Sound Detected')
                    sample = None
                    return True
    
    
    # button functions
    def on_t3start(): 
        global soundcheck, soundon, soundoff
        print('Listening')
        
        # opening test audio frame
        troubleshootFrame3.grid_forget()
        testaudioframe.grid(sticky='nsew')
        taf_instruction.configure(text = '')
        # initialise sound test variables
        soundcheck = 0
        soundon    = 0
        soundoff   = 0
        
        def soundCheckLoop():
            global soundcheck, soundon, soundoff
            while soundcheck<5 and soundon<3 and soundoff <3:
                taf_instruction.configure(text = 'Make a Sound', text_color= UIfont['normal'])
                print('Make a sound')
                tstart = time.time()
                while(time.time() - tstart < 10):
                    soundDetect = detectSound()
                    time.sleep(0.1) 
                    if soundDetect:
                        taf_instruction.configure(text = 'Sound Detected', text_color= UIfont['success'])
                        soundcheck = soundcheck +1
                        soundon = soundon +1
                        break
                if not soundDetect:        
                    print("Stopped listening after timeout")
                    taf_instruction.configure(text = 'Sound Not Detected', text_color= UIfont['error'])
                    soundcheck = soundcheck +1
                    soundoff = soundoff +1
                time.sleep(2)
                
            if soundon==3: 
                taf_instruction.configure(text = 'Sound Check Complete! All sounds were detected')
                # wait for a while to show save feedback and then goto main frame
                testaudioframe.after(3000, lambda: (testaudioframe.grid_forget(), troubleshootFrame3.grid(sticky='nsew')))
            elif soundoff==3:
                taf_instruction.configure(text = 'Could not detect sounds. Adjust the gain and try testing again')
                # wait for a while to show save feedback and then goto main frame
                testaudioframe.after(3000, lambda: (testaudioframe.grid_forget(), troubleshootFrame3.grid(sticky='nsew')))
    
        
        # running in thread to avoid freezing UI         
        threading.Thread(target=soundCheckLoop).start()
        
    def on_t3stop():
        killstat = LSLkiller(deviceName)
        if killstat:
            time.sleep(3)
            troubleshootFrame3.grid_forget()
            mainFrame.grid(sticky='nsew')
            
        
    
    
    # title 
    t3_title =  customtkinter.CTkLabel(troubleshootFrame3, text= 'Troubleshoot nEEGlace', font=H2)
    t3_title.grid(row=0, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (40,0))
    # device status
    t3_devicestat = customtkinter.CTkLabel(troubleshootFrame3, text= 'Device Status:', font=B2, text_color='#979797', justify= 'left')
    t3_devicestat.grid(row=1, column=0, sticky='w', padx= (40,0), pady= (2,0))
    t3_devicestatans = customtkinter.CTkLabel(troubleshootFrame3, text= 'ON', font=B2, text_color='#2cd756', justify= 'left')
    t3_devicestatans.grid(row=1, column=0, sticky='w', padx= (125,0), pady= (2,0))
    t3_ampstat = customtkinter.CTkLabel(troubleshootFrame3, text= 'Amplifier Status:', font=B2, text_color='#979797', justify= 'left')
    t3_ampstat.grid(row=1, column=1, sticky='w', padx= (0,0), pady= (2,0))
    t3_ampstatans = customtkinter.CTkLabel(troubleshootFrame3, text= 'Streaming', font=B2, text_color='#2cd756', justify= 'left')
    t3_ampstatans.grid(row=1, column=1, sticky='w', padx= (100,0), pady= (2,0))
    # body font
    t3_body1 = customtkinter.CTkLabel(troubleshootFrame3, text= 'Step 3', font=H3, justify= 'left')
    t3_body1.grid(row=2, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (0,0))
    t3_bodystr = 'Now lets test the sound stream to check if nEEGlace is able \nto detect the audio'
    t3_body2 = customtkinter.CTkLabel(troubleshootFrame3, text= t3_bodystr, font=B1, justify= 'left')
    t3_body2.grid(row=2, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (60,0))
    # instructions
    t3_Q1str = 'Click on the Start Testing Audio button below and make loud \nsounds to test the audio detection'
    t3_Q1 = customtkinter.CTkLabel(troubleshootFrame3, text= t3_Q1str, font=B1, text_color='#979797', justify= 'left')
    t3_Q1.grid(row=3, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (10,0))
    
    # quit button
    t3_BTquit = customtkinter.CTkButton(troubleshootFrame3, text= 'Quit Stream', fg_color='#5b2b2b', text_color='#b6b6b6', hover_color='#4f2121',
                                        command= on_t3stop)
    t3_BTquit.grid(row=9, column=0, sticky='sw', padx= (40,0), pady= (0,40))
    # start button
    t3_BTstartsoundcheck = customtkinter.CTkButton(troubleshootFrame3, text= 'Start Testing Audio',
                                                   command= on_t3start)
    t3_BTstartsoundcheck.grid(row=9, column=9, sticky='se', padx= (10,40), pady= (0,40))
    
    
    
    # UI for test audio frame
    taf_instruction = customtkinter.CTkLabel(testaudioframe, text= '', font=B1, justify= 'center')
    taf_instruction.grid(row=1, column=0, columnspan= 10, sticky='ew', pady= (180,0))
    desc_str = 'Make a sharp sound when instructed to test if the nEEglace can create audio triggers. If the audio trigger is \nunable to be picked, either make a loud sound or adjust the gain in the nEEglace configure window.'
    taf_decription =  customtkinter.CTkLabel(testaudioframe, text= desc_str, font=B2, text_color= UIfont['notes'], justify= 'center')
    taf_decription.grid(row=2, column=0, columnspan= 10, sticky='ew', pady= (200,0))
    
    # padx= (90,0), padx= (300,0), 
    
    # --- Configure Main Frame UI ---
    
    # button functions
    def on_cfgmback():
        configFrameMain.grid_forget()
        mainFrame.grid(sticky='nsew')
        
    def on_cfgmsave():
        global bela_micgain, bela_thresh, bela_record, bela_recorddur, stream_erpavg, stream_tmin, stream_tmax, belawritestatus
        bela_micgain   = cfgM_gainentry.get() 
        bela_thresh    = cfgM_threshentry.get()
        bela_record    = cfgM_recordtoggleVar.get()
        bela_recorddur = cfgM_durentry.get()
        stream_erpavg  = cfgM_trlavgentry.get()
        stream_tmin    = cfgM_epminentry.get()
        stream_tmax    = cfgM_epmaxentry.get()
        
        # check input conditions
        if int(bela_micgain) > 55:
           bela_micgain = '55' 
           cfgM_gainentry.delete(0, 'end')
           cfgM_gainentry.insert(0, bela_micgain)
           tkinter.messagebox.showwarning("Warning", "Microphone gain exceeds the maximum allowed value of 55. It has been reset to 55.")
        
        if int(bela_recorddur) > 720:
           bela_recorddur = '720' 
           cfgM_durentry.delete(0, 'end')
           cfgM_durentry.insert(0, bela_recorddur)
           tkinter.messagebox.showwarning("Warning", "Record duration exceeds the maximum allowed value of 720sec. It has been reset to 720sec.")
              
        # write data to config file
        dumpConfig()
        # update bela
        belastatus = checkBelaStatus()
        if belastatus:    
            belawritestatus = updateBela()
            if not belawritestatus:
                cfgM_infonotestr = 'Error saving to Bela Board. Verify the connection and try again'
                cfgM_infonote.configure(text = cfgM_infonotestr, text_color= UIfont['error'])
                
            else:
                cfgM_infonotestr = 'Changes made to the settings are saved'
                cfgM_infonote.configure(text = cfgM_infonotestr, text_color= UIfont['success'])
                # wait for a while to show save feedback and then goto main frame
                configFrameMain.after(1400, lambda: (configFrameMain.grid_forget(), mainFrame.grid(sticky='nsew')))
        else:
            cfgM_infonotestr = 'Changes made to the settings are saved'
            cfgM_infonote.configure(text = cfgM_infonotestr, text_color= UIfont['success'])
            # wait for 2sec to show save feedback and then goto main frame
            configFrameMain.after(1400, lambda: (configFrameMain.grid_forget(), mainFrame.grid(sticky='nsew')))
    
    def on_connectbela():
        configFrameMain.grid_forget()
        configFrameMain.grid(sticky='nsew')
        updateConfig()
        if belastatus:
            cfgM_gaintxt.configure(text_color= UIfont['normal'])
            cfgM_gainentry.configure(state= 'normal', border_color= UItextbox['active']['boxborder'], fg_color= UItextbox['active']['boxbg'], text_color= UItextbox['active']['boxfont'])
            cfgM_threshtxt.configure(text_color= UIfont['normal'])
            cfgM_threshentry.configure(state= 'normal', border_color= UItextbox['active']['boxborder'], fg_color= UItextbox['active']['boxbg'], text_color= UItextbox['active']['boxfont'])
            cfgM_recordtxt.configure(text_color= UIfont['normal'])
            cfgM_recordtoggle.configure(state= 'normal', fg_color= UItextbox['active']['boxborder'])
            cfgM_durtxt.configure(text_color= UIfont['normal'])
            cfgM_durentry.configure(state= 'normal', border_color= UItextbox['active']['boxborder'], fg_color= UItextbox['active']['boxbg'], text_color= UItextbox['active']['boxfont'])
            # info note
            cfgM_infonotestr = ''
            cfgM_infonote.configure(text = cfgM_infonotestr)
            
            
        
        
    def cfgM_recordtoggleEvent():
        if cfgM_recordtoggleVar.get() == 1:
            cfgM_durentry.configure(state= 'normal', border_color= '#565b5e', fg_color= '#343638', text_color= UItextbox['active']['boxfont'])
            cfgM_recordtoggle.configure(text= 'ON')
        if cfgM_recordtoggleVar.get() == 0:
            cfgM_durentry.configure(state= 'disabled', border_color= '#343638', fg_color= '#2b2b2b', text_color= UItextbox['deactive']['boxfont'])
            cfgM_recordtoggle.configure(text= 'OFF')
           
    # fetch config data
    updateConfig()
    configdata = fetchConfig()
    
    # title 
    cfgM_title =  customtkinter.CTkLabel(configFrameMain, text= 'Configure nEEGlace', font=H2)
    cfgM_title.grid(row=0, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (40,0))
    # bela setings
    cfgM_title1 = customtkinter.CTkLabel(configFrameMain, text= 'Bela Board Settings', font=B1, text_color='#979797', justify= 'left')
    cfgM_title1.grid(row=1, column=0, columnspan= 5, sticky='w', padx= (40,0), pady= (40,0))
    # input gain
    cfgM_gaintxt = customtkinter.CTkLabel(configFrameMain, text= 'Microphone Input Gain', font=B1)
    cfgM_gaintxt.grid(row=2, column=0, sticky='w', padx= (40,0), pady= (10,0))
    cfgM_gainentry = customtkinter.CTkEntry(configFrameMain, width= 48)
    cfgM_gainentry.insert(0, configdata[0])
    cfgM_gainentry.grid(row=2, column=2, sticky='w', padx= (10,0), pady= (10,0))
    # energy threshold
    cfgM_threshtxt = customtkinter.CTkLabel(configFrameMain, text= 'Energy Threshold', font=B1)
    cfgM_threshtxt.grid(row=3, column=0, sticky='w', padx= (40,0), pady= (0,0))
    cfgM_threshentry = customtkinter.CTkEntry(configFrameMain, width= 48)
    cfgM_threshentry.insert(0, configdata[1])
    cfgM_threshentry.grid(row=3, column=2, sticky='w', padx= (10,0), pady= (10,0))
    # audio setings
    cfgM_title2 = customtkinter.CTkLabel(configFrameMain, text= 'Audio Recording', font=B1, text_color='#979797', justify= 'left')
    cfgM_title2.grid(row=4, column=0, columnspan= 5, sticky='w', padx= (40,0), pady= (20,0))
    # record audio
    cfgM_recordtxt = customtkinter.CTkLabel(configFrameMain, text= 'Record Audio', font=B1)
    cfgM_recordtxt.grid(row=5, column=0, sticky='w', padx= (40,0), pady= (10,0))
    cfgM_recordtoggleVar = customtkinter.IntVar()
    cfgM_recordtoggleVar.set(configdata[2])
    # setting values based on record status 
    if cfgM_recordtoggleVar.get() == 1:
        toggletext = 'ON'
        dur_state = 'normal'
        dur_border = UItextbox['active']['boxborder']
        dur_fg = UItextbox['active']['boxbg']
        dur_txtclr = UItextbox['active']['boxfont']
    elif cfgM_recordtoggleVar.get() == 0:
        toggletext = 'OFF'
        dur_state = 'disabled'
        dur_border = UItextbox['deactive']['boxborder']
        dur_fg = UItextbox['deactive']['boxbg']
        dur_txtclr = UItextbox['deactive']['boxfont']
    cfgM_recordtoggle = customtkinter.CTkSwitch(configFrameMain, variable= cfgM_recordtoggleVar, text= toggletext,
                                                onvalue= 1, offvalue= 0, command= cfgM_recordtoggleEvent)
    cfgM_recordtoggle.grid(row=5, column=2, sticky='w', padx= (10,0), pady= (10,0))
    # # record duration
    cfgM_durtxt = customtkinter.CTkLabel(configFrameMain, text= 'Record Duration (s)', font=B1)
    cfgM_durtxt.grid(row= 6, column=0, sticky='w', padx= (40,0), pady= (10,0))
    cfgM_durentry = customtkinter.CTkEntry(configFrameMain, width= 48)
    cfgM_durentry.insert(0, configdata[3])
    cfgM_durentry.configure(state= dur_state, border_color= dur_border, fg_color= dur_fg, text_color= dur_txtclr)
    
    cfgM_durentry.grid(row=6, column=2, sticky='w', padx= (10,0), pady= (10,0))
    # stream settings 
    cfgM_title3 = customtkinter.CTkLabel(configFrameMain, text= 'Stream Settings', font=B1, text_color='#979797', justify= 'left')
    cfgM_title3.grid(row=1, column=7, columnspan= 5, sticky='w', padx= (0,0), pady= (40,0))
    # trial averaged gain
    cfgM_trlavgtxt = customtkinter.CTkLabel(configFrameMain, text= 'Trial to Average for ERP', font=B1)
    cfgM_trlavgtxt.grid(row=2, column=7, sticky='w', padx= (0,0), pady= (10,0))
    cfgM_trlavgentry = customtkinter.CTkEntry(configFrameMain, width= 48)
    cfgM_trlavgentry.insert(0, configdata[4])
    cfgM_trlavgentry.grid(row=2, column=9, sticky='w', padx= (10,0), pady= (10,0))
    # epoch min
    cfgM_epmintxt = customtkinter.CTkLabel(configFrameMain, text= 'Epoch Min (s)', font=B1)
    cfgM_epmintxt.grid(row=3, column=7, sticky='w', padx= (0,0), pady= (10,0))
    cfgM_epminentry = customtkinter.CTkEntry(configFrameMain, width= 48)
    cfgM_epminentry.insert(0, configdata[5])
    cfgM_epminentry.grid(row=3, column=9, sticky='w', padx= (10,0), pady= (10,0))
    # epoch max
    cfgM_epmaxtxt = customtkinter.CTkLabel(configFrameMain, text= 'Epoch Max (s)', font=B1)
    cfgM_epmaxtxt.grid(row=4, column=7, sticky='w', padx= (0,0), pady= (0,0))
    cfgM_epmaxentry = customtkinter.CTkEntry(configFrameMain, width= 48)
    cfgM_epmaxentry.insert(0, configdata[6])
    cfgM_epmaxentry.grid(row=4, column=9, sticky='w', padx= (10,0), pady= (0,0))
    
    # info note
    cfgM_infonotestr = ''
    cfgM_infonote = customtkinter.CTkLabel(configFrameMain, text= cfgM_infonotestr, font=B2, text_color= UIfont['notes'], justify= 'left')
    cfgM_infonote.grid(row=8, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (24,0))
    
    # back button
    cfgM_BTback2main = customtkinter.CTkButton(configFrameMain, text= 'Back to Main Menu', fg_color='#5b5b5b', text_color='#b6b6b6', hover_color='#4f4f4f', 
                                     command= on_cfgmback)
    cfgM_BTback2main.grid(row=9, column=0, sticky='sw', padx= (40,0), pady= (0,40))
    
    # save button
    cfgM_BTsave = customtkinter.CTkButton(configFrameMain, text= 'Save Changes',
                                        command= on_cfgmsave)
    cfgM_BTsave.grid(row=9, column=9, sticky='se', padx= (10,40), pady= (0,40))
    
    if not belastatus:
        cfgM_gaintxt.configure(text_color= UIfont['deactive'])
        cfgM_gainentry.configure(state= 'disabled', border_color= UItextbox['deactive']['boxborder'], fg_color= UItextbox['deactive']['boxbg'], text_color= UItextbox['deactive']['boxfont'])
        cfgM_threshtxt.configure(text_color= UIfont['deactive'])
        cfgM_threshentry.configure(state= 'disabled', border_color= UItextbox['deactive']['boxborder'], fg_color= UItextbox['deactive']['boxbg'], text_color= UItextbox['deactive']['boxfont'])
        cfgM_recordtxt.configure(text_color= UIfont['deactive'])
        cfgM_recordtoggle.configure(state= 'disabled', fg_color= UItextbox['deactive']['boxborder'])
        cfgM_durtxt.configure(text_color= UIfont['deactive'])
        cfgM_durentry.configure(state= 'disabled', border_color= UItextbox['deactive']['boxborder'], fg_color= UItextbox['deactive']['boxbg'], text_color= UItextbox['deactive']['boxfont'])
        # info note
        cfgM_infonotestr = 'NOTE: Bela board is not connected to the computer. To make changes to the Bela Board Settings, Connect Bela Board \nto computer via USB and click Connect Bela.'
        cfgM_infonote.configure(text = cfgM_infonotestr)
        # connect bella button
        cfgM_BTconnectbela = customtkinter.CTkButton(configFrameMain, text= 'Connect Bela', fg_color='#ffffff', text_color='#000000', hover_color='#979797',
                                           command= on_connectbela)
        cfgM_BTconnectbela.grid(row=9, column=2, sticky='sw', padx= (0,10), pady= (0,40))
    
    
    
    # --- Streamer Load Frame UI ---     
    strL_body = customtkinter.CTkLabel(streamerFrameLoad, text= 'Connecting to LSL', font=B2, text_color= UIfont['normal'], justify= 'center')
    strL_body.grid(row=0, column=0, columnspan= 10, sticky='ew', pady= (200,0))
    strL_bar = customtkinter.CTkProgressBar(streamerFrameLoad, progress_color= '#ffffff', height= 2, corner_radius=2)
    strL_bar.grid(row=1, column=0, sticky='ew', padx= (245,0), pady= (10,0))
    strL_bar.start()
    
    
    # --- Streamer Main Frame UI ---
    
    # button functions
    def on_streameeg():
        plotEEG(inlet, eegchans, nbchans, tidx, soundThresh)
        trialcount = 0
        
        # def update_trialcount():
        #     nonlocal trialcount
        #     while True: 
        #         if newtrialcount > trialcount:
        #             trialcount = newtrialcount
        #             strM_trlavgans.configure(text= trialcount)
        #             strM_sndstatans.configure(text= 'Sound Detected')
        #             time.sleep(.3)
        #             strM_sndstatans.configure(text= '')
        #         time.sleep(1)
                
    def on_impcalc(): 
        print('Currently this Functionality Not Available')
        # ani = start_erp(srate, nchan= nbchans, datainlet= inlet[0])
        # # start_erp(srate, nchan= nbchans, datainlet= inlet[0])
        # trialcount = 0
        
        # def update_trialcount():
        #     nonlocal trialcount
        #     while True: 
        #         newtrialcount = getTrialCount()
        #         if newtrialcount > trialcount:
        #             trialcount = newtrialcount
        #             strM_trlavgans.configure(text= trialcount)
        #             strM_sndstatans.configure(text= 'Sound Detected')
        #             time.sleep(.3)
        #             strM_sndstatans.configure(text= '')
        #         time.sleep(1)
            
        # threading.Thread(target=update_trialcount, daemon=True).start()
        # plt.show()
    
    def on_streamquit():
        killstat = LSLkiller(deviceName)
        if killstat:
            time.sleep(3)
            streamerFrameMain.grid_forget()
            mainFrame.grid(sticky='nsew')
        
        
    
    # title 
    strM_title =  customtkinter.CTkLabel(streamerFrameMain, text= 'Stream nEEGlace', font=H2)
    strM_title.grid(row=0, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (40,0))
    # body text '
    strM_bodystr = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor\nincididunt ut labore et dolore magna aliqua.'
    strM_body = customtkinter.CTkLabel(streamerFrameMain, text= bodystr, font=B2, text_color='#979797', justify= 'left')
    strM_body.grid(row=2, column=0, columnspan= 10, sticky='w', padx= (40,0), pady= (10,0))
    
    
    # stream info
    strM_title1 = customtkinter.CTkLabel(streamerFrameMain, text= 'Sream Info', font=B1, text_color='#979797', justify= 'left')
    strM_title1.grid(row=3, column=0, columnspan= 5, sticky='w', padx= (40,0), pady= (60,0))
    # sfreq
    sfreq = 40
    strM_sfreqtxt = customtkinter.CTkLabel(streamerFrameMain, text= 'Sampling Frequency', font=B1)
    strM_sfreqtxt.grid(row=4, column=0, columnspan= 5, sticky='w', padx= (40,0), pady= (10,0))
    strM_sfreqans = customtkinter.CTkLabel(streamerFrameMain, text= f'{sfreq} Hz', font=B1)
    strM_sfreqans.grid(row=4, column=2, columnspan= 5, sticky='w', padx= (0,0), pady= (10,0))
    # channel count
    nchanx = 8
    strM_nchantxt = customtkinter.CTkLabel(streamerFrameMain, text= 'Number of Channels', font=B1)
    strM_nchantxt.grid(row=5, column=0, columnspan= 5, sticky='w', padx= (40,0), pady= (0,0))
    strM_nchanans = customtkinter.CTkLabel(streamerFrameMain, text= f'{nchanx} Channels', font=B1)
    strM_nchanans.grid(row=5, column=2, columnspan= 5, sticky='w', padx= (0,0), pady= (0,0))
    # trigger count
    trgchan = 7
    strM_trgchantxt = customtkinter.CTkLabel(streamerFrameMain, text= 'Trigger Channel', font=B1)
    strM_trgchantxt.grid(row=6, column=0, columnspan= 5, sticky='w', padx= (40,0), pady= (0,0))
    strM_trgchanans = customtkinter.CTkLabel(streamerFrameMain, text= f'{trgchan}', font=B1)
    strM_trgchanans.grid(row=6, column=2, columnspan= 5, sticky='w', padx= (0,0), pady= (0,0))
    # audio recording status
    recordstaus = 'On'
    strM_recordtxt = customtkinter.CTkLabel(streamerFrameMain, text= 'Audio Recording', font=B1)
    strM_recordtxt.grid(row=7, column=0, columnspan= 5, sticky='w', padx= (40,0), pady= (0,0))
    strM_recordans = customtkinter.CTkLabel(streamerFrameMain, text= f'{recordstaus}', font=B1)
    strM_recordans.grid(row=7, column=2, columnspan= 5, sticky='w', padx= (0,0), pady= (0,0))
    
    # plot info
    strM_title3 = customtkinter.CTkLabel(streamerFrameMain, text= 'Plot Info', font=B1, text_color='#979797', justify= 'left')
    strM_title3.grid(row=3, column=7, columnspan= 5, sticky='w', padx= (0,0), pady= (60,0))
    # trials averaged
    trlcount = 0
    strM_trlavgtxt = customtkinter.CTkLabel(streamerFrameMain, text= 'Trial Count', font=B1)
    strM_trlavgtxt.grid(row=4, column=7, columnspan= 5, sticky='w', padx= (0,0), pady= (10,0))
    strM_trlavgans = customtkinter.CTkLabel(streamerFrameMain, text= f'{trlcount}', font=B1)
    strM_trlavgans.grid(row=4, column=9, sticky='w', padx= (80,0), pady= (10,0))
    # sound detector
    sndstat = ''
    strM_sndstattxt = customtkinter.CTkLabel(streamerFrameMain, text= 'Trigger', font=B1)
    strM_sndstattxt.grid(row=5, column=7, columnspan= 5, sticky='w', padx= (0,0), pady= (0,0))
    strM_sndstatans = customtkinter.CTkLabel(streamerFrameMain, text= f'{sndstat}', font=B1, text_color='#2cd756')
    strM_sndstatans.grid(row=5, column=9, columnspan= 5, sticky='w', padx= (80,0), pady= (0,0))
    
    # quit button
    strM_BTquit = customtkinter.CTkButton(streamerFrameMain, text= 'Quit Stream', fg_color='#5b2b2b', text_color='#b6b6b6', hover_color='#4f2121',
                                          command= on_streamquit)
    strM_BTquit.grid(row=9, column=0, sticky='sw', padx= (40,0), pady= (0,40))
    # ERP button 
    strM_BTerp = customtkinter.CTkButton(streamerFrameMain, text= 'Check Impedance', fg_color='#ffffff', text_color='#000000', hover_color='#979797',
                                         command= on_impcalc)
    strM_BTerp.grid(row=9, column=9, sticky='se', padx= (0,190), pady= (0,40))
    # Plot Stream button
    strM_BTeegstream = customtkinter.CTkButton(streamerFrameMain, text= 'Plot EEG Data', fg_color='#ffffff', text_color='#000000', hover_color='#979797',
                                               command= on_streameeg)
    strM_BTeegstream.grid(row=9, column=9, sticky='se', padx= (10,40), pady= (0,40))
    
    

    
    # --- Impedance Frame UI ---

    circle_radius = 22
    # convert impedance value to colors
    def convertImpval2Color(impedance):
        impedance = max(0, min(impedance, 100)) 
        red = int((impedance / 100) * 255)
        green = int(((100 - impedance) / 100) * 255)
        return f'#{red:02x}{green:02x}00' 
    
    # electrode layout
    def drawElectrodes(positions):
        item_pairs = []
        for i, (x, y) in enumerate(positions):
            circle_id = imp_canvas.create_oval(
                x - circle_radius, y - circle_radius,
                x + circle_radius, y + circle_radius,
                fill='#404040', outline="#626262"
            )
            text_id = imp_canvas.create_text(
                x, y, text="0.00", fill="black", font=("Arial", 9, "bold")
            )
            item_pairs.append((circle_id, text_id))
        return item_pairs

    # updates impedance for each electrode
    def setImpColors(canvas, electrode_items, impedance_values):
        for i, (circle_id, text_id) in enumerate(electrode_items):
            color = convertImpval2Color(impedance_values[i])
            canvas.itemconfig(circle_id, fill=color)
            canvas.itemconfig(text_id, text=f"{impedance_values[i]:.2f}")
    
    def on_impquit():
        impedanceFrame.grid_forget()
        mainFrame.grid(sticky='nsew')
    
    def on_impstart():
        # example values (10 for left, 8 for right)
        example_impedances = [5, 12, 20, 28, 36, 45, 60, 72, 85, 95, 10, 20, 30, 40, 55, 65, 75, 90]
        setImpColors(imp_canvas, electrode_items, example_impedances)
    
    # Title
    imp_title = customtkinter.CTkLabel(impedanceFrame, text='Impedance', font=H2)
    imp_title.grid(row=0, column=0, columnspan=10, sticky='w', padx=(40, 0), pady=(40, 0))
    
    # Buttons
    imp_BTstartimp = customtkinter.CTkButton(impedanceFrame, text='Measure Impedance', fg_color='#ffffff',
                                             text_color='#000000', hover_color='#979797', command=on_impstart)
    imp_BTstartimp.grid(row=9, column=9, sticky='se', padx=(10, 40), pady=(0, 40))
    
    imp_BTquit = customtkinter.CTkButton(impedanceFrame, text='Back to Main Menu', fg_color='#5b5b5b',
                                         text_color='#b6b6b6', hover_color='#4f4f4f', command=on_impquit)
    imp_BTquit.grid(row=9, column=0, sticky='sw', padx=(40, 0), pady=(0, 40))
    
    # canvas for electrode layout
    imp_canvas = customtkinter.CTkCanvas(impedanceFrame, width=500, height=350, bg="#2b2b2b", highlightthickness=0)
    imp_canvas.grid(row=2, column=6, columnspan=10, pady=(20, 0))
    
    # electrode positions
    left_positions = [(45, 74), (84, 37), (131, 41), (168, 81), (185, 130), (185, 186),
                      (168, 235), (131, 275), (84, 279), (45, 242)]
    right_positions = [(417, 74), (378, 37), (331, 41), (277, 130), (294, 235),
                       (331, 275), (378, 279), (417, 242)]
    

    

    
    
    
    
    
    
    # run app
    app.mainloop()
    
    pass