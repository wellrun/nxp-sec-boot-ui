import wx
import sys, os

BOOT_SEQ_COLOR_INVALID   = wx.Colour( 160, 160, 160 )
BOOT_SEQ_COLOR_INACTIVE  = wx.Colour( 166, 255, 255 )
BOOT_SEQ_COLOR_ACTIVE    = wx.Colour( 147, 255, 174 )

MCU_DEVICE_iMXRT102x = 'i.MXRT102x'
MCU_DEVICE_iMXRT105x = 'i.MXRT105x'
MCU_DEVICE_iMXRT106x = 'i.MXRT106x'

SECURE_BOOT_TYPE_DEVELOPMENT = 'Unsigned (XIP) image Boot'
SECURE_BOOT_TYPE_HAB_AUTH    = 'Signed (XIP) Image Boot'
SECURE_BOOT_TYPE_HAB_CRYPTO  = 'HAB Signed Encrypted Image Boot'
SECURE_BOOT_TYPE_BEE_CRYPTO  = 'BEE (Signed) Encrypted XIP Image Boot'

KEY_STORAGE_REGION_OPTMK      = 'Fuse OTPMK'
KEY_STORAGE_REGION_GP4        = 'Fuse GP4'
KEY_STORAGE_REGION_SW_GP2     = 'Fuse SW_GP2 '
KEY_STORAGE_REGION_GP4_SW_GP2 = 'Fuse GP4&SW_GP2'