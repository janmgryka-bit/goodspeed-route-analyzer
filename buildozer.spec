[app]

# (str) Title of your application
title = GoodSpeed Route Analyzer

# (str) Package name
package.name = goodspeedrouteanalyzer

# (str) Package domain (needed for android/ios packaging)
package.domain = org.goodspeed

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (str) Application versioning (method 1)
version = 0.1

# (str) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.1.0,plyer,kivy-garden.mapview,importlib

# (str) Custom source folders for requirements
# requirements.source.kivy = ../../kivy

# (str) Presplash of the application
# presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
# icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

#
# OSX Specific
#

#
# author = © Copyright Info

# change the major version of python used by the app
osx.python_version = 3

# Kivy version to use
osx.kivy_version = 2.1.0

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash animation using Lottie format.
# See https://lottie.github.io/lottie-spec/ for examples and https://airbnb.design/lottie/
# for general documentation.
# Lottie files can be created using various tools, like Adobe After Effect, Synfig, Blender.
#presplash.lottie = "path/to/lottie/file.json"

# (string) Presplash animation in low res Android Device. 768x1024
#presplash.lottie_landscape.phone = "path/to/lottie/file.json"
# (string) Presplash animation in high res Android Device. 768x1024
#presplash.lottie_landscape.tablet = "path/to/lottie/file.json"
# (string) Presplash animation in low res Android Device in portrait mode. 768x1024
#presplash.lottie_portrait.phone = "path/to/lottie/file.json"
# (string) Presplash animation in high res Android Device in portrait mode. 768x1024
#presplash.lottie_portrait.tablet = "path/to/lottie/file.json"

# (list) Permissions
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,ACCESS_BACKGROUND_LOCATION

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android SDK version to use
android.sdk = 33

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded.)
#android.ant_path =

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you just want to test/build your package
android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only. If set to False,
# the default, you will be shown the license when first running
# buildozer.
android.accept_sdk_license = True

# (str) The archs to build for, choices: armeabi-v7a, arm64-v8a, all
# In past, was `android.arch` as we weren't supporting builds for multiple archs at the same time.
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) The format used to package the app for release mode (aab or apk).
# android.release_artifact = aab

# (str) The format used to package the app for debug mode (apk or aab).
# android.debug_artifact = apk

#
# Python for android (p4a) specific
#

# (str) The directory in which python-for-android should look for your own build recipes (if any)
#p4a.local_recipes =

# (str) The directory in which python-for-android should look for your own build modules (if any)
#p4a.local_modules =

# (str) The entry point for your application. Default is main.py
main = goodspeed_route_analyzer.py

# (str) Full name including package path of the application where the main.py live
#app.entrypoint = goodspeed_route_analyzer:main

# (str) The name of the main class of the application
#app.class_name = RouteAnalyzerApp

# (list) List of application to update with the dbs listed in argument.
#apps =

# (str) The name of the requirements file
#requirements.file = requirements.txt

# (str) The name of the requirements file for the second arch
#requirements.ndk_second = requirements.ndk_second.txt

# (list) List of requirements to include in the .apk file
#requirements.source.kivy = ../../kivy

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
#orientation = portrait

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

#
# iOS specific
#

# (str) Path to a custom kivy-ios folder
#ios.kivy_ios_dir = ../kivy-ios
# Alternately, specify the URL and branch of a git checkout:
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

# Another platform dependency: ios-deploy
# Uncomment to use a custom checkout
#ios.ios_deploy_dir = ../ios_deploy
# Or specify URL and branch
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.7.0

# (bool) Whether or not to sign the code
ios.codesign.allowed = false

# (str) Name of the certificate to use for signing the debug version
# Get a list of available identities: buildozer ios list_identities
#ios.codesign.debug = "iPhone Developer: <lastname> <firstname> (<hexstring>)"

# (str) The development team that has signed the certificate
#ios.codesign.development_team.debug = <hexstring>

# (str) The development team that has signed the certificate
#ios.codesign.development_team.release = %(ios.codesign.development_team.debug)s

# (str) Name of the certificate to use for signing the release version
#ios.codesign.release = %(ios.codesign.debug)s

# (str) URL to an .app file
#ios.app = %(source.dir)s/app.ipa

# (str) URL to an .app file
#ios.app = %(source.dir)s/app.ipa

# (str) Application versioning (method 1)
#ios.version = 0.1

# (str) Application versioning (method 2)
#ios.version.regex = __version__ = ['"](.*)['"]
#ios.version.filename = %(source.dir)s/main.py

# (list) List of application to update with the dbs listed in argument.
#ios.apps =

# (str) Xcode project configuration
#ios.xcode.config = Debug

# (str) Xcode project configuration for Release
#ios.xcode.config.release = Release

# (str) Xcode project configuration for Release (App Store)
#ios.xcode.config.release_appstore = Release

# (str) Xcode project configuration for Release (Ad Hoc)
#ios.xcode.config.release_adhoc = Release

# (str) Xcode project configuration for Release (Enterprise)
#ios.xcode.config.release_enterprise = Release

# (str) Xcode project configuration for Release (Development)
#ios.xcode.config.release_development = Release

# (str) Xcode project configuration for Release (Testing)
#ios.xcode.config.release_testing = Release

# (str) Xcode project configuration for Release (App Store)
#ios.xcode.config.release_appstore = Release

# (str) Xcode project configuration for Release (Ad Hoc)
#ios.xcode.config.release_adhoc = Release

# (str) Xcode project configuration for Release (Enterprise)
#ios.xcode.config.release_enterprise = Release

# (str) Xcode project configuration for Release (Development)
#ios.xcode.config.release_development = Release

# (str) Xcode project configuration for Release (Testing)
#ios.xcode.config.release_testing = Release

# (str) Xcode project configuration for Release (App Store)
#ios.xcode.config.release_appstore = Release

# (str) Xcode project configuration for Release (Ad Hoc)
#ios.xcode.config.release_adhoc = Release

# (str) Xcode project configuration for Release (Enterprise)
#ios.xcode.config.release_enterprise = Release

# (str) Xcode project configuration for Release (Development)
#ios.xcode.config.release_development = Release

# (str) Xcode project configuration for Release (Testing)
#ios.xcode.config.release_testing = Release

# (str) Xcode project configuration for Release (App Store)
#ios.xcode.config.release_appstore = Release

# (str) Xcode project configuration for Release (Ad Hoc)
#ios.xcode.config.release_adhoc = Release

# (str) Xcode project configuration for Release (Enterprise)
#ios.xcode.config.release_enterprise = Release

# (str) Xcode project configuration for Release (Development)
#ios.xcode.config.release_development = Release

# (str) Xcode project configuration for Release (Testing)
#ios.xcode.config.release_testing = Release

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
# build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .ipa) storage
# bin_dir = ./bin

