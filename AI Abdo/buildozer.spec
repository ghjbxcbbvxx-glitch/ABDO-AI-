[app]

title = ABDO AI

package.name = abdoai

package.domain = com.abdoai

source.dir = .

source.include_exts = py,json,kv,png,jpg,jpeg,svg,ttf

version = 2.0.0

requirements = python3,kivy,requests,arabic-reshaper,python-bidi

orientation = portrait

fullscreen = 0

android.permissions = INTERNET

icon.filename = assets/icon.png


[buildozer]

log_level = 2

warn_on_root = 1


[android]

android.api = 35

android.minapi = 23

android.archs = arm64-v8a, armeabi-v7a

android.accept_sdk_license = True