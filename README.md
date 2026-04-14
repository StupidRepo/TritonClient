# Triton GUI Client
A (probably) cross-platform PySide6 GUI app for interacting with the [triton.squid.wtf](https://triton.squid.wtf/) API, to enjoy high-quality music offline.

## Features
- [ ] Searching
  - [x] Tracks
  - [x] Albums
  - [ ] Artists
  - [x] Playlists
- [x] Downloading
    - [x] Tracks
      - [x] Metadata (Tagging)
      - [x] Cover Art
    - [x] Albums
    - [x] Playlists
- [ ] Streaming

## Installation
1. Clone the repository.
2. Create a virtual environment and activate it.
3. Install the required packages:
   - `pip install -r requirements.txt`
4. Install FFMPEG.
   - On Windows, download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.
   - On macOS, use Homebrew: `brew install ffmpeg`
   - On Linux, use your package manager, e.g., `sudo apt install ffmpeg` for Debian-based systems.
   - For anything else, you're probably capable enough to do some googling.
5. Run the application:
   - `python main.py`

## Usage
1. Launch the application.
2. Use the search bar to find tracks or playlists.
3. Switch betweens track/playlist/album search using the dropdown.
4. Click "Search" to display results.
5. For tracks, click one and press "Add to Queue" or click & drag to select multiple songs.
    - Shift-clicking works too, to select multiple tracks.
6. Click "Add selected to Queue" to add selected tracks to the playback queue.
7. When done selecting tracks, click "Show Queue" and then "Download Queue" to download all queued tracks.
8. Downloaded tracks will be saved in a `Downloads/_TritonMusic/` folder in your user profile's home directory, with proper metadata and cover art.
  - Albums are stored in subfolders named after the album, and playlists are stored in subfolders named after the playlist.
9. Enjoy your music!

## Notes
- To download all music in a playlist/album:
    1. Find the playlist/album.
    2. Double-click it to open it.
    3. Click on "Download Playlist" or "Download Album".
    4. Playlist will automatically start downloading to your `Downloads` folder in a subfolder named after the playlist/album.
- Make sure FFMPEG is correctly installed and accessible via PATH for proper audio processing.

## Screenshots
| Title                                | Image                                                           |
|--------------------------------------|-----------------------------------------------------------------|
| **Main Window (Track view)**         | ![Main Window (Track view)](screenshots/tracks-main.png)        |
| **Main Window (Playlist view)**      | ![Main Window (Playlist view)](screenshots/playlists-main.png)  |
| **Playlist opened (double-clicked)** | ![Playlist (double-clicked)](screenshots/playlist-selected.png) |
| **Queue**                            | ![Queue](screenshots/dl-queue.png)                              |
| **Queue (Downloading)**              | ![Queue (Downloading)](screenshots/dl-queue-dl.png)             |
| **Metadata Tagging Showoff**         | ![Metadata Tagging](screenshots/metadata-showoff.png)           |


## Credits
- Me, for making this.
- [@uimaxbai](https://github.com/uimaxbai), for providing [the API](https://github.com/uimaxbai/hifi-api).
- [PySide6](https://pypi.org/project/PySide6/), for the GUI.
