#! /usr/bin/env python
# -*- coding: UTF-8 -*-
import wx
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import os
import time
from mem import memcore
from ui import uidef
from fuse import fusedef
from ui import ui_cfg_flexspinor
from ui import ui_cfg_flexspinand
from ui import ui_cfg_semcnor
from ui import ui_cfg_semcnand
from ui import ui_cfg_usdhcsd
from ui import ui_cfg_usdhcmmc
from ui import ui_cfg_lpspinor
from ui import ui_settings_cert
from ui import ui_settings_fixed_otpmk_key
from ui import ui_settings_flexible_user_keys

kRetryPingTimes = 5

kBootloaderType_Rom         = 0
kBootloaderType_Flashloader = 1

class secBootMain(memcore.secBootMem):

    def __init__(self, parent):
        memcore.secBootMem.__init__(self, parent)
        self.connectStage = uidef.kConnectStage_Rom
        self.gaugeTimer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.increaseGauge, self.gaugeTimer)

    def _startGaugeTimer( self ):
        self.initGauge()
        #self.gaugeTimer.Start(500) # ms

    def _stopGaugeTimer( self ):
        #self.gaugeTimer.Stop()
        self.deinitGauge()

    def callbackSetMcuSeries( self, event ):
        self.setTargetSetupValue()

    def callbackSetMcuDevice( self, event ):
        self.setTargetSetupValue()
        self.createMcuTarget()
        usbIdList = self.getUsbid()
        self.adjustPortSetupValue(self.connectStage, usbIdList)
        self.applyFuseOperToRunMode()

    def callbackSetBootDevice( self, event ):
        self.setTargetSetupValue()
        self.setSecureBootSeqColor()

    def callbackBootDeviceConfiguration( self, event ):
        if self.bootDevice == uidef.kBootDevice_FlexspiNor:
            if self.tgt.isSipFlexspiNorDevice:
                self.popupMsgBox('MCU has on-chip QSPI NOR Flash (4MB, 133MHz), so you don\'t need to configure this boot device!')
            else:
                flexspiNorFrame = ui_cfg_flexspinor.secBootUiCfgFlexspiNor(None)
                flexspiNorFrame.SetTitle(u"FlexSPI NOR Device Configuration")
                flexspiNorFrame.Show(True)
        elif self.bootDevice == uidef.kBootDevice_FlexspiNand:
            flexspiNandFrame = ui_cfg_flexspinand.secBootUiFlexspiNand(None)
            flexspiNandFrame.SetTitle(u"FlexSPI NAND Device Configuration")
            flexspiNandFrame.Show(True)
        elif self.bootDevice == uidef.kBootDevice_SemcNor:
            semcNorFrame = ui_cfg_semcnor.secBootUiSemcNor(None)
            semcNorFrame.SetTitle(u"SEMC NOR Device Configuration")
            semcNorFrame.Show(True)
        elif self.bootDevice == uidef.kBootDevice_SemcNand:
            semcNandFrame = ui_cfg_semcnand.secBootUiCfgSemcNand(None)
            semcNandFrame.SetTitle(u"SEMC NAND Device Configuration")
            semcNandFrame.Show(True)
        elif self.bootDevice == uidef.kBootDevice_UsdhcSd:
            usdhcSdFrame = ui_cfg_usdhcsd.secBootUiUsdhcSd(None)
            usdhcSdFrame.SetTitle(u"uSDHC SD Device Configuration")
            usdhcSdFrame.Show(True)
        elif self.bootDevice == uidef.kBootDevice_UsdhcMmc:
            usdhcMmcFrame = ui_cfg_usdhcmmc.secBootUiUsdhcMmc(None)
            usdhcMmcFrame.SetTitle(u"uSDHC MMC Device Configuration")
            usdhcMmcFrame.Show(True)
        elif self.bootDevice == uidef.kBootDevice_LpspiNor:
            lpspiNorFrame = ui_cfg_lpspinor.secBootUiCfgLpspiNor(None)
            lpspiNorFrame.SetTitle(u"LPSPI NOR/EEPROM Device Configuration")
            lpspiNorFrame.Show(True)
        else:
            pass

    def callbackSetUartPort( self, event ):
        self.setPortSetupValue(self.connectStage)

    def callbackSetUsbhidPort( self, event ):
        usbIdList = self.getUsbid()
        self.setPortSetupValue(self.connectStage, usbIdList)

    def callbackSetOneStep( self, event ):
        if not self.isToolRunAsEntryMode:
            self.getOneStepConnectMode()
        else:
            self.initOneStepConnectMode()
            self.popupMsgBox('One Step mode cannot be set under Entry Mode, Please switch to Master Mode and try again!')

    def _retryToPingBootloader( self, bootType ):
        pingStatus = False
        pingCnt = kRetryPingTimes
        while (not pingStatus) and pingCnt > 0:
            if bootType == kBootloaderType_Rom:
                pingStatus = self.pingRom()
            elif bootType == kBootloaderType_Flashloader:
                pingStatus = self.pingFlashloader()
            else:
                pass
            if pingStatus:
                break
            pingCnt = pingCnt - 1
            if self.isUsbhidPortSelected:
                time.sleep(2)
        return pingStatus

    def _connectStateMachine( self ):
        connectSteps = uidef.kConnectStep_Normal
        self.getOneStepConnectMode()
        if self.isOneStepConnectMode and self.connectStage != uidef.kConnectStage_Reset:
            connectSteps = uidef.kConnectStep_Fast
        while connectSteps:
            self.updatePortSetupValue()
            if self.connectStage == uidef.kConnectStage_Rom:
                self.connectToDevice(self.connectStage)
                if self._retryToPingBootloader(kBootloaderType_Rom):
                    self.getMcuDeviceInfoViaRom()
                    self.getMcuDeviceHabStatus()
                    if self.jumpToFlashloader():
                        self.connectStage = uidef.kConnectStage_Flashloader
                        self.updateConnectStatus('yellow')
                        usbIdList = self.getUsbid()
                        self.adjustPortSetupValue(self.connectStage, usbIdList)
                    else:
                        self.updateConnectStatus('red')
                        self.popupMsgBox('MCU has entered ROM SDP mode but failed to jump to Flashloader, Please reset board and try again!')
                        return
                else:
                    self.updateConnectStatus('red')
                    self.popupMsgBox('Make sure that you have put MCU in SDP (Serial Downloader Programming) mode (BMOD[1:0] pins = 2\'b01)!')
                    return
            elif self.connectStage == uidef.kConnectStage_Flashloader:
                self.connectToDevice(self.connectStage)
                if self._retryToPingBootloader(kBootloaderType_Flashloader):
                    self.getMcuDeviceInfoViaFlashloader()
                    self.getMcuDeviceBtFuseSel()
                    self.updateConnectStatus('green')
                    self.connectStage = uidef.kConnectStage_ExternalMemory
                else:
                    self.connectStage = uidef.kConnectStage_Rom
                    self.updateConnectStatus('red')
                    self.popupMsgBox('Failed to ping Flashloader, Please reset board and consider updating flashloader.srec file under /src/targets/ then try again!')
                    return
            elif self.connectStage == uidef.kConnectStage_ExternalMemory:
                if self.configureBootDevice():
                    self.getBootDeviceInfoViaFlashloader()
                    self.connectStage = uidef.kConnectStage_Reset
                    self.updateConnectStatus('blue')
                else:
                    self.connectStage = uidef.kConnectStage_Rom
                    self.updateConnectStatus('red')
                    self.popupMsgBox('MCU has entered Flashloader but failed to configure external memory, Please reset board and set proper boot device then try again!')
                    return
            elif self.connectStage == uidef.kConnectStage_Reset:
                self.resetMcuDevice()
                self.connectStage = uidef.kConnectStage_Rom
                self.updateConnectStatus('black')
                usbIdList = self.getUsbid()
                self.adjustPortSetupValue(self.connectStage, usbIdList)
                self.connectToDevice(self.connectStage)
            else:
                pass
            connectSteps -= 1

    def callbackConnectToDevice( self, event ):
        self._startGaugeTimer()
        self.printLog("'Connect to xxx' button is clicked")
        self._connectStateMachine()
        self._stopGaugeTimer()

    def callbackSetSecureBootType( self, event ):
        self.setSecureBootSeqColor()

    def callbackAllInOneAction( self, event ):
        allInOneSeqCnt = 1
        directReuseCert = False
        while allInOneSeqCnt:
            status = False
            if self.secureBootType == uidef.kSecureBootType_HabAuth or \
               self.secureBootType == uidef.kSecureBootType_HabCrypto or \
               (self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice == uidef.kBootDevice_FlexspiNor and self.isCertEnabledForBee):
                status = self._doGenCert(directReuseCert)
                if not status:
                    return
                status = self._doProgramSrk()
                if not status:
                    return
            status = self._doGenImage()
            if not status:
                return
            if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice == uidef.kBootDevice_FlexspiNor:
                status = self._doBeeEncryption()
                if not status:
                    return
                if self.keyStorageRegion == uidef.kKeyStorageRegion_FlexibleUserKeys:
                    status = self._doProgramBeeDek()
                    if not status:
                        return
                elif self.keyStorageRegion == uidef.kKeyStorageRegion_FixedOtpmkKey:
                    if self.isCertEnabledForBee:
                        # If HAB is not closed here, we need to close HAB and re-do All-In-One Action
                        if self.mcuDeviceHabStatus != fusedef.kHabStatus_Closed0 and \
                           self.mcuDeviceHabStatus != fusedef.kHabStatus_Closed1:
                            self.enableHab()
                            self._connectStateMachine()
                            while self.connectStage != uidef.kConnectStage_Reset:
                                self._connectStateMachine()
                            directReuseCert = True
                            allInOneSeqCnt += 1
                else:
                    pass
            status = self._doFlashImage()
            if not status:
                return
            if self.secureBootType == uidef.kSecureBootType_HabCrypto:
                status = self._doFlashHabDek()
                if not status:
                    return
            allInOneSeqCnt -= 1
        self.invalidateStepButtonColor(uidef.kSecureBootSeqStep_AllInOne)

    def callbackAdvCertSettings( self, event ):
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice != uidef.kBootDevice_FlexspiNor:
            self.popupMsgBox('Action is not available because BEE encryption boot is only designed for FlexSPI NOR device!')
        elif self.secureBootType != uidef.kSecureBootType_Development:
            if self.secureBootType == uidef.kSecureBootType_BeeCrypto and (not self.isCertEnabledForBee):
                self.popupMsgBox('Certificate is not enabled for BEE, You can enable it then try again!')
            else:
                certSettingsFrame = ui_settings_cert.secBootUiSettingsCert(None)
                certSettingsFrame.SetTitle(u"Advanced Certificate Settings")
                certSettingsFrame.Show(True)
                self.updateAllCstPathToCorrectVersion()
        else:
            self.popupMsgBox('No need to set certificate option when booting unsigned image!')

    def _wantToReuseAvailableCert( self, directReuseCert ):
        certAnswer = wx.NO
        if self.isCertificateGenerated(self.secureBootType):
            if not directReuseCert:
                msgText = (("There is available certificate, Do you want to reuse existing certificate? \n"))
                certAnswer = wx.MessageBox(msgText, "Certificate Question", wx.YES_NO | wx.ICON_QUESTION)
                if certAnswer == wx.NO:
                    msgText = (("New certificate will be different even you don’t change any settings, Do you really want to have new certificate? \n"))
                    certAnswer = wx.MessageBox(msgText, "Certificate Question", wx.YES_NO | wx.ICON_QUESTION)
                    if certAnswer == wx.YES:
                        certAnswer = wx.NO
                    else:
                        certAnswer = wx.YES
            else:
                certAnswer = wx.YES
        return (certAnswer == wx.YES)

    def _doGenCert( self, directReuseCert=False ):
        status = False
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice != uidef.kBootDevice_FlexspiNor:
            self.popupMsgBox('Action is not available because BEE encryption boot is only designed for FlexSPI NOR device!')
        elif self.secureBootType != uidef.kSecureBootType_Development:
            if self.secureBootType == uidef.kSecureBootType_BeeCrypto and (not self.isCertEnabledForBee):
                self.popupMsgBox('Certificate is not enabled for BEE, You can enable it then try again!')
            else:
                self._startGaugeTimer()
                self.printLog("'Generate Certificate' button is clicked")
                self.updateAllCstPathToCorrectVersion()
                if not self._wantToReuseAvailableCert(directReuseCert):
                    if self.createSerialAndKeypassfile():
                        self.setSecureBootButtonColor()
                        self.genCertificate()
                        self.genSuperRootKeys()
                        self.showSuperRootKeys()
                        status = True
                else:
                    status = True
                self._stopGaugeTimer()
        else:
            self.popupMsgBox('No need to generate certificate when booting unsigned image!')
        return status

    def callbackGenCert( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doGenCert()
        else:
            self.popupMsgBox('Separated action is not available under Entry Mode, You should use All-In-One Action!')

    def callbackChangedAppFile( self, event ):
        self.getUserAppFilePath()
        self.setSecureBootButtonColor()

    def _doGenImage( self ):
        status = False
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice != uidef.kBootDevice_FlexspiNor:
            self.popupMsgBox('Action is not available because BEE encryption boot is only designed for FlexSPI NOR device!')
        else:
            self._startGaugeTimer()
            self.printLog("'Generate Bootable Image' button is clicked")
            if self.createMatchedAppBdfile():
                if self.genBootableImage():
                    self.showHabDekIfApplicable()
                    status = True
            self._stopGaugeTimer()
        return status

    def callbackGenImage( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doGenImage()
        else:
            self.popupMsgBox('Separated action is not available under Entry Mode, You should use All-In-One Action!')

    def callbackSetCertForBee( self, event ):
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto:
            self.setBeeCertColor()

    def callbackSetKeyStorageRegion( self, event ):
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto:
            self.setKeyStorageRegionColor()

    def callbackAdvKeySettings( self, event ):
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice == uidef.kBootDevice_FlexspiNor:
            if self.keyStorageRegion == uidef.kKeyStorageRegion_FixedOtpmkKey:
                otpmkKeySettingsFrame = ui_settings_fixed_otpmk_key.secBootUiSettingsFixedOtpmkKey(None)
                otpmkKeySettingsFrame.SetTitle(u"Advanced Key Settings - Fixed OTPMK")
                otpmkKeySettingsFrame.Show(True)
            elif self.keyStorageRegion == uidef.kKeyStorageRegion_FlexibleUserKeys:
                userKeySettingsFrame = ui_settings_flexible_user_keys.secBootUiSettingsFlexibleUserKeys(None)
                userKeySettingsFrame.SetTitle(u"Advanced Key Settings - Flexible User")
                userKeySettingsFrame.setNecessaryInfo(self.mcuDevice, self.tgt.flexspiNorMemBase)
                userKeySettingsFrame.Show(True)
            else:
                pass
        else:
            self.popupMsgBox('Key setting is only available when booting BEE encrypted image in FlexSPI NOR device!')

    def _doBeeEncryption( self ):
        status = False
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice == uidef.kBootDevice_FlexspiNor:
            self._startGaugeTimer()
            if self.keyStorageRegion == uidef.kKeyStorageRegion_FixedOtpmkKey:
                if self.connectStage == uidef.kConnectStage_Reset:
                    if not self.prepareForFixedOtpmkEncryption():
                        self.popupMsgBox('Failed to prepare for fixed OTPMK SNVS encryption, Please reset board and try again!')
                    else:
                        status = True
                else:
                    self.popupMsgBox('Please configure boot device via Flashloader first!')
            elif self.keyStorageRegion == uidef.kKeyStorageRegion_FlexibleUserKeys:
                self.encrypteImageUsingFlexibleUserKeys()
                status = True
            else:
                pass
            self._stopGaugeTimer()
        else:
            self.popupMsgBox('BEE encryption is only available when booting BEE encrypted image in FlexSPI NOR device!')
        return status

    def callbackDoBeeEncryption( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doBeeEncryption()
        else:
            self.popupMsgBox('Separated action is not available under Entry Mode, You should use All-In-One Action!')

    def _doProgramSrk( self ):
        status = False
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice != uidef.kBootDevice_FlexspiNor:
            self.popupMsgBox('Action is not available because BEE encryption boot is only designed for FlexSPI NOR device!')
        elif self.secureBootType != uidef.kSecureBootType_Development:
            if self.secureBootType == uidef.kSecureBootType_BeeCrypto and (not self.isCertEnabledForBee):
                self.popupMsgBox('Certificate is not enabled for BEE, You can enable it then try again!')
            else:
                if self.connectStage == uidef.kConnectStage_ExternalMemory or \
                   self.connectStage == uidef.kConnectStage_Reset:
                    self._startGaugeTimer()
                    self.printLog("'Load SRK data' button is clicked")
                    if self.burnSrkData():
                        status = True
                    self._stopGaugeTimer()
                else:
                    self.popupMsgBox('Please connect to Flashloader first!')
        else:
            self.popupMsgBox('No need to burn SRK data when booting unsigned image!')
        return status

    def callbackProgramSrk( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doProgramSrk()
        else:
            self.popupMsgBox('Separated action is not available under Entry Mode, You should use All-In-One Action!')

    def _doProgramBeeDek( self ):
        status = False
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice == uidef.kBootDevice_FlexspiNor:
            if self.keyStorageRegion == uidef.kKeyStorageRegion_FlexibleUserKeys:
                if self.connectStage == uidef.kConnectStage_ExternalMemory or \
                   self.connectStage == uidef.kConnectStage_Reset:
                    self._startGaugeTimer()
                    if self.burnBeeDekData():
                        status = True
                    self._stopGaugeTimer()
                else:
                    self.popupMsgBox('Please connect to Flashloader first!')
            else:
                self.popupMsgBox('No need to burn BEE DEK data as OTPMK key is selected!')
        else:
            self.popupMsgBox('BEE DEK Burning is only available when booting BEE encrypted image in FlexSPI NOR device!')
        return status

    def callbackProgramBeeDek( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doProgramBeeDek()
        else:
            self.popupMsgBox('Separated action is not available under Entry Mode, You should use All-In-One Action!')

    def _doFlashImage( self ):
        status = False
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice != uidef.kBootDevice_FlexspiNor:
            self.popupMsgBox('Action is not available because BEE encryption boot is only designed for FlexSPI NOR device!')
        else:
            if self.connectStage == uidef.kConnectStage_Reset:
                self._startGaugeTimer()
                self.printLog("'Load Bootable Image' button is clicked")
                if not self.flashBootableImage():
                    self.popupMsgBox('Failed to flash bootable image into external memory, Please reset board and try again!')
                else:
                    if self.burnBootDeviceFuses():
                        if (self.secureBootType == uidef.kSecureBootType_HabAuth) or \
                           (self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.isCertEnabledForBee):
                            if self.mcuDeviceHabStatus != fusedef.kHabStatus_Closed0 and \
                               self.mcuDeviceHabStatus != fusedef.kHabStatus_Closed1:
                                self.enableHab()
                        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice == uidef.kBootDevice_FlexspiNor:
                            if self.burnBeeKeySel():
                                status = True
                        else:
                            status = True
                self._stopGaugeTimer()
            else:
                self.popupMsgBox('Please configure boot device via Flashloader first!')
        return status

    def callbackFlashImage( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doFlashImage()
        else:
            self.popupMsgBox('Separated action is not available under Entry Mode, You should use All-In-One Action!')

    def _doFlashHabDek( self ):
        status = False
        if self.secureBootType == uidef.kSecureBootType_BeeCrypto and self.bootDevice != uidef.kBootDevice_FlexspiNor:
            self.popupMsgBox('Action is not available because BEE encryption boot is only designed for FlexSPI NOR device!')
        elif self.secureBootType == uidef.kSecureBootType_HabCrypto:
            if self.connectStage == uidef.kConnectStage_Reset:
                self._startGaugeTimer()
                self.printLog("'Load KeyBlob Data' button is clicked")
                if self.mcuDeviceHabStatus != fusedef.kHabStatus_Closed0 and \
                   self.mcuDeviceHabStatus != fusedef.kHabStatus_Closed1:
                    self.enableHab()
                    self._connectStateMachine()
                    while self.connectStage != uidef.kConnectStage_Reset:
                        self._connectStateMachine()
                self.flashHabDekToGenerateKeyBlob()
                status = True
                self._stopGaugeTimer()
            else:
                self.popupMsgBox('Please configure boot device via Flashloader first!')
        else:
            self.popupMsgBox('KeyBlob loading is only available when booting HAB encrypted image!')
        return status

    def callbackFlashHabDek( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doFlashHabDek()
        else:
            self.popupMsgBox('Separated action is not available under Entry Mode, You should use All-In-One Action!')

    def callbackScanFuse( self, event ):
        if self.connectStage == uidef.kConnectStage_ExternalMemory or \
           self.connectStage == uidef.kConnectStage_Reset:
            self._startGaugeTimer()
            self.scanAllFuseRegions()
            self._stopGaugeTimer()
        else:
            self.popupMsgBox('Please connect to Flashloader first!')

    def callbackBurnFuse( self, event ):
        if self.connectStage == uidef.kConnectStage_ExternalMemory or \
           self.connectStage == uidef.kConnectStage_Reset:
            self._startGaugeTimer()
            self.burnAllFuseRegions()
            self._stopGaugeTimer()
        else:
            self.popupMsgBox('Please connect to Flashloader first!')

    def callbackViewMem( self, event ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self.readProgrammedMemoryAndShow()
        else:
            self.popupMsgBox('Please configure boot device via Flashloader first!')

    def callbackClearMem( self, event ):
        self.clearMem()

    def _doReadMem( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self.readBootDeviceMemory()
        else:
            self.popupMsgBox('Please configure boot device via Flashloader first!')

    def callbackReadMem( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doReadMem()
        else:
            self.popupMsgBox('Common memory operation is not available under Entry Mode, Please switch to Master Mode and try again!')

    def _doEraseMem( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self.eraseBootDeviceMemory()
        else:
            self.popupMsgBox('Please configure boot device via Flashloader first!')

    def callbackEraseMem( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doEraseMem()
        else:
            self.popupMsgBox('Common memory operation is not available under Entry Mode, Please switch to Master Mode and try again!')

    def _doWriteMem( self ):
        if self.connectStage == uidef.kConnectStage_Reset:
            self.writeBootDeviceMemory()
        else:
            self.popupMsgBox('Please configure boot device via Flashloader first!')

    def callbackWriteMem( self, event ):
        if not self.isToolRunAsEntryMode:
            self._doWriteMem()
        else:
            self.popupMsgBox('Common memory operation is not available under Entry Mode, Please switch to Master Mode and try again!')

    def callbackClearLog( self, event ):
        self.clearLog()

    def callbackExit( self, event ):
        exit(0)

    def _switchToolRunMode( self ):
        self.applyFuseOperToRunMode()

    def callbackSetEntryMode( self, event ):
        self.setToolRunMode()
        self._switchToolRunMode()

    def callbackSetMasterMode( self, event ):
        self.setToolRunMode()
        self._switchToolRunMode()

    def callbackShowHomePage( self, event ):
        msgText = (('https://github.com/JayHeng/nxp-sec-boot-ui.git \n'))
        wx.MessageBox(msgText, "Home Page", wx.OK | wx.ICON_INFORMATION)

    def callbackShowAboutAuthor( self, event ):
        author = "Author:  衡杰Jay、李嘉奕Joyee \n"
        blog = "Blog:      痞子衡嵌入式 https://www.cnblogs.com/henjay724/ \n"
        msgText = ((author.encode('utf-8')) +
                   ('Email:     jie.heng@nxp.com \n') +
                   ('Email:     hengjie1989@foxmail.com \n') +
                   (blog.encode('utf-8')))
        wx.MessageBox(msgText, "About Author", wx.OK | wx.ICON_INFORMATION)

    def callbackShowSpecialThanks( self, event ):
        helper = "Special thanks to 周小朋Clare、杨帆、刘华东Howard \n"
        msgText = ((helper.encode('utf-8')))
        wx.MessageBox(msgText, "Special Thanks", wx.OK | wx.ICON_INFORMATION)

if __name__ == '__main__':
    app = wx.App()

    main_win = secBootMain(None)
    main_win.SetTitle(u"nxpSecBoot v0.11.2")
    main_win.Show()

    app.MainLoop()
