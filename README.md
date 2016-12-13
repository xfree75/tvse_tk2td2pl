# tvse_tk2td2pl
python script. running by crontab.

## contained two python script.

### First script (html parsing and download torrent file)
- check new epsoide: tor\*\*\*\*k\*\* html parsing by config(keywords).
- download torrent file: https client.
- copy to watch-dir.
- remove old torrent files.
- control status json file.
- control queue json file: It needs real downloaded file name. It is not torrent file name.
- set to crontab: 2~3 times for a day.

### Second script (move to plex library path(by config) and modify filename(by config))
- check file copy complete of transmission-daemon.
- search file useing TV Show series-name, episode-number, season-number(option, nullable)
- modify filename by config: plex season Naming 'Series' & 'Season' Based TV Shows.
- copy to plex library path(by config with {series_title}/Season XX/{series_title} - sXXeYY.ext)
- control status json file.
- control queue json file: It needs real downloaded file name. It is not torrent file name.
- set to crontab: every minutes.

