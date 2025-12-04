[app]

title = Finance Assistant
package.name = financeapp
package.domain = org.vika
version = 0.1
source.dir = .
source.include.exts = py,png,jpg,kv,ttf,json,xml,txt,db


source.include.patterns = main.py, flamingo.png, users.db, assets/*, assets/icons/*, kv/*, screens/*, utils/*

p4a.python_version = 3.11

requirements = python3,kivy==2.3.1,pillow,numpy,requests,pycryptodome,filetype,plyer
orientation = portrait
fullscreen = 0

# Виправлення для іконки:
icon.filename = %(source.dir)s/flamingo.png


[android]

api = 33
minapi = 21
ndk = 25b


android.permissions = INTERNET,ACCESS_NETWORK_STATE,VIBRATE,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,FOREGROUND_SERVICE,READ_EXTERNAL_STORAGE

android.allow_backup = True
android.archs = arm64-v8a,armeabi-v7a,x86_64
android.accept_sdk.license = True
android.skip.update = False
android.gradle_args = -Xmx2048M -Dorg.gradle.daemon=true -Dorg.gradle.internal.http.connectionTimeout=600000 -Dorg.gradle.internal.http.socketTimeout=600000


[app:source.exclude.patterns]
*.pyc
__pycache__
*.log
.git
venv/

[buildozer]

log_level = 5

warn_on_root = 0