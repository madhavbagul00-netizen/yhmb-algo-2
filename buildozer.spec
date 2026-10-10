[app]
title = YHMB ALGO APP
package.name = yhmbalgo
package.domain = org.yhmb
source.dir = .
source.include_exts = py,png,jpg,kv,ttf,json
version = 1.0
requirements = python3,kivy==2.3.0,requests,pyotp,certifi,urllib3,idna,charset-normalizer,websocket-client,logzero,pycryptodome
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 34
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
