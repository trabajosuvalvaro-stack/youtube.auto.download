"""Use native OS trust without disabling certificate/hostname verification."""
import truststore
truststore.inject_into_ssl()
import yt_dlp
if __name__ == '__main__':
    yt_dlp.main()
