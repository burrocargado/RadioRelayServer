 
=======================
RadioRelayServer
=======================
* This is for listening to "radiko" radio service in JAPAN.
  You cannot use this outside JAPAN due to restriction of radiko service.
* Music Player Daemon (MPD)でラジコを聞くための中継サーバです。
* ラジコで聞くことができる放送局の一覧をプレイリストとして自動生成します。
  MPDでこれを読み込んで選局します。
* 放送局の切り替えは1秒程度、そこそこ快適にチャンネルザッピングできると思います。
* NanoPi-NEO(Ubuntu 16.04.5 LTS)で動作確認しています。
 
Requirement
===========
 
:Python: 3.5.2
:Django: 2.1.5
:ffmpeg: 2.8.14
 
 
Quick start
===========
1. プロジェクトのクローン::
 
    git clone https://github.com/burrocargado/RadioRelayServer
 
2. モデルのmigrate::
 
    モデルは使っていませんが、
    python manage.py migrate
 
3. 設定::
    
    MPDは別途用意してください。
    ffmpegを使いますのでPathを通しておいてください。
    settings/config.pyにプレイリストファイルとストリーミングURLを設定。
    ラジコプレミアムのアカウントがあれば、settings/account.pyに設定。
 
4. 起動::
    
    python manage.py runserver 0.0.0.0:9000
    
    上記設定のストリーミングURLに対応させてください。
    
    Error: You don't have permission to access that port.
    これが表示される場合
    
    sudo touch /var/lib/mpd/playlists/00_radiko.m3u
    sudo chmod 666 /var/lib/mpd/playlists/00_radiko.m3u
    
    とでもしてくささい。
 
5. 使い方::
　　　　
    お使いのMPDクライアントから上記のプレイリスト（設定を変えていなければ00_radiko.m3u）
    を読み込んで選局してください。

