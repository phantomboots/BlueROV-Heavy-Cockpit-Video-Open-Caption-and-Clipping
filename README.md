This Python code uses ffmpeg to rename .mp4 files recorded from the BlueROV Heavy to the NDST standard file naming convention 
of:

CruiseName_DiveName_YYYYMMDD_HHMMSS. Where the time and date are UTC date and time.

The script then search for .ass subtitles and hard encodes these subtitles into the video (Open Captioning).

Lastly, the script clips the video file into smaller, more manageable 10 min chunk. It shoudl be expected that processing will
take several hours for long duration/many video files.
