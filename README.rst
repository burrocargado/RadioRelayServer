 
=======================
RadioRelayServer
=======================
* This is for listening to "radiko" radio service in JAPAN.
  You cannot use this outside JAPAN due to restriction of radiko service.
* Music Player Daemon (MPD)でラジコを聞くための中継サーバです。
* ラジコで聞くことができる放送局の一覧をプレイリストとして自動生成します。
  MPDでこれを読み込んで選局します。
  また、WEBインターフェースから選局、番組表からダウンロードや予約録音できます。
* 放送局の切り替えは1秒程度、そこそこ快適にチャンネルザッピングできると思います。
* NanoPi-NEO2(Ubuntu 16.04.4 LTS)で動作確認しています。
 
Requirement
===========
:Python: 3.5.2
:Django: 2.2
:django-background-tasks: 1.2.0
:python-mpd2: 1.0
:GStreamer: 1.14.4
 
Quick start
===========

1. 依存するソフトウエアのインストール::

    audo apt-get update
    sudo apt-get install gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-tools
    sudo apt-get install python3-pip
    sudo -H pip3 install --upgrade pip
    sudo -H pip3 install virtualenv
    virtualenv -p /usr/bin/python3 ~/radio
    source ~/radio/bin/activate

2. プロジェクトのクローンと依存するPythonモジュールのインストール::

    git clone https://github.com/burrocargado/RadioRelayServer
    cd RadioRelayServer
    git checkout develop
    pip install -r requirements.txt

3. モデルのマイグレーション::

    python manage.py makemigrations
    python manage.py migrate

4. 管理者アカウントの作成::

    python add_admin.py
    python manage.py loaddata default_admin.json

5. 設定::

    MPDは別途インストール、設定してください。
    radio/local_settings.pyを作成。
    詳細はlocal_settings_sample.py参照、
    SECRET_KEYはgenerate_secretkey_setting.pyを用いて生成、
    ALLOWED_HOSTSにDjangoを実行するホストのIPアドレスを追加。
    MPD_ADDRにMPDを実行するホストのIPアドレスを設定
    MPD_PORTにMPDのポート番号を設定
    BASE_URL='http://127.0.0.1:9000' のIPアドレスをDjangoを実行するホストのIPアドレスに修正

6. 起動::

    python manage.py runserver 0.0.0.0:9000　（サーバー本体）
    python manage.py process_tasks --queue update-program （番組表更新タスク）
    python manage.py process_tasks --queue downoad （タイムフリーダウンロード用タスク）
    python manage.py process_tasks --queue timer_rec （予約録音用タスク）

7. 使い方::

    お使いのMPDクライアントから上記のプレイリスト（設定を変えていなければ00_radiko.m3u）
    を読み込んで選局してください。
    
    Webインターフェース
    http://xxx.xxx.xxx.xxx:9000/radiko/station
    IPアドレス部分はDjangoを実行するホストのアドレス

