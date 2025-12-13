from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Slot, Qt, Signal, QMetaObject, Q_ARG, QThread
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import MAX_CONCURRENT_DOWNLOADS
from controllers.app_controller import AppController, DownloadCallbacks
from models.playlist import Playlist
from models.track import Track
from utils.cover import load_cover_pixmap
from utils.formatting import format_duration, format_track_listing
from widgets.playlist_list_widget import PlaylistListWidget
from widgets.track_list_widget import TrackListWidget


def _format_queue_entry(track: Track) -> str:
    return format_track_listing(track)


# noinspection PyUnusedLocal
class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Triton Client")
        self.controller = AppController()
        self._current_playlist: Playlist | None = None
        self._current_playlist_tracks: list[Track] = []

        self.dropdown = QComboBox()
        self.dropdown.addItems(self.controller.categories())
        self.search_input = QLineEdit()
        self.search_button = QPushButton("Search")

        self.queue_button = QPushButton("Add selected to queue (0)")
        self.queue_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.show_queue_button = QPushButton("Show Queue (0)")
        self.show_queue_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.dropdown)
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(self.search_button)
        top_layout.addStretch()
        top_layout.addWidget(self.queue_button)
        top_layout.addWidget(self.show_queue_button)

        self.track_list = TrackListWidget()
        self.playlist_list = PlaylistListWidget()

        self.playlist_header = PlaylistHeaderWidget()
        self.playlist_tracks = TrackListWidget()
        playlist_page = QWidget()
        self.playlist_page = playlist_page
        playlist_layout = QVBoxLayout(playlist_page)
        playlist_layout.setContentsMargins(0, 0, 0, 0)
        playlist_layout.setSpacing(8)
        playlist_layout.addWidget(self.playlist_header)
        playlist_layout.addWidget(self.playlist_tracks)

        self.details_stack = QStackedWidget()
        self.details_stack.addWidget(self.track_list)
        self.details_stack.addWidget(self.playlist_list)
        self.details_stack.addWidget(playlist_page)
        self.details_stack.setCurrentWidget(self.track_list)

        self.notice_label = QLabel("Cannot search this type yet, please try Tracks or Playlists.")
        self.notice_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notice_label.setVisible(False)

        root_layout = QVBoxLayout(self)
        root_layout.addLayout(top_layout)
        root_layout.addWidget(self.details_stack)
        root_layout.addWidget(self.notice_label)

        self.playlist_list.playlist_activated.connect(self.on_playlist_selected)
        self.playlist_header.download_requested.connect(self.on_download_playlist)
        self.search_button.clicked.connect(self.on_search_clicked)
        self.queue_button.clicked.connect(self.on_queue_selected)
        self.show_queue_button.clicked.connect(self.on_show_queue)
        self.track_list.itemSelectionChanged.connect(self._refresh_add_button_label)
        self.playlist_tracks.itemSelectionChanged.connect(self._refresh_add_button_label)
        self._refresh_add_button_label()
        self._update_queue_label()

    def _active_track_list(self) -> TrackListWidget:
        current_widget = self.details_stack.currentWidget()
        if current_widget is self.track_list:
            return self.track_list
        if current_widget is self.playlist_page:
            return self.playlist_tracks
        # default to main tracks list when playlists page or others selected
        return self.track_list

    def _update_queue_label(self) -> None:
        self.show_queue_button.setText(f"Show Queue ({self.controller.queue_size()})")

    def _download_queue_tracks(self, progress_dialog: DownloadProgressDialog | None = None) -> None:
        def _start(track: Track, completed: int, total: int, worker_id: int) -> None:
            if progress_dialog:
                progress_dialog.start_track_safe(track, worker_id)

        def _progress(downloaded: int, total: int, worker_id: int) -> None:
            if progress_dialog:
                progress_dialog.report_current_progress_safe(downloaded, total, worker_id)

        def _completed(done: int, total: int, worker_id: int) -> None:
            if progress_dialog:
                progress_dialog.track_completed_safe(done, worker_id)

        def _is_cancelled() -> bool:
            return progress_dialog.is_cancelled() if progress_dialog else False

        self.controller.download_queue_parallel(
            DownloadCallbacks(
                track_started=_start,
                track_progress=_progress,
                track_completed=_completed,
                is_cancelled=_is_cancelled,
            )
        )

    def _download_queue_with_progress(self) -> None:
        if self.controller.queue_is_empty():
            return
        dialog = DownloadProgressDialog(total_tracks=self.controller.queue_size(), parent=self)

        # Create worker thread for downloading
        worker = DownloadWorker(lambda: self._download_queue_tracks(progress_dialog=dialog))
        worker.finished.connect(lambda: self._on_download_finished(dialog))
        worker.error_occurred.connect(lambda error: self._on_download_error(error, dialog))

        dialog.show()
        worker.start()
        dialog.exec()  # Block until dialog is closed

    def _on_download_finished(self, dialog: DownloadProgressDialog) -> None:
        dialog.accept()
        self._update_queue_label()

    def _on_download_error(self, error: str, dialog: DownloadProgressDialog) -> None:
        dialog.accept()
        QMessageBox.critical(
            self,
            "Download Error",
            f"An error occurred during download:\n{error}"
        )
        self._update_queue_label()

    @Slot()
    def on_search_clicked(self) -> None:
        category = self.dropdown.currentText()
        query = self.search_input.text().strip()
        if not query:
            return
        try:
            results = self.controller.search(category, query)
            if category == "Tracks":
                self.notice_label.hide()
                self.details_stack.setCurrentWidget(self.track_list)
                self.track_list.setVisible(True)
                self.track_list.load_tracks(results)
            elif category == "Playlists":
                self.notice_label.hide()
                self.details_stack.setCurrentWidget(self.playlist_list)
                self.playlist_list.load_playlists(results)
            else:
                self.details_stack.setCurrentWidget(self.track_list)
                self.track_list.clear()
                self.track_list.setVisible(False)
                self.notice_label.setVisible(True)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Search Error",
                f"Failed to perform search:\n{str(e)}"
            )

    @Slot()
    def on_queue_selected(self) -> None:
        tracks = self._active_track_list().selected_tracks()
        if not tracks:
            return
        added = self.controller.add_to_queue(tracks)
        if added:
            self._update_queue_label()

    @Slot()
    def on_download_queue(self) -> None:
        if self.controller.queue_is_empty():
            return
        self._download_queue_tracks()
        self._update_queue_label()

    @Slot()
    def on_show_queue(self) -> None:
        dialog = QueueDialog(
            controller=self.controller,
            download_callback=self._download_queue_with_progress,
            queue_changed_callback=self._update_queue_label,
            parent=self,
        )
        dialog.exec()

    @Slot(Playlist)
    def on_playlist_selected(self, playlist: Playlist) -> None:
        try:
            detail, tracks = self.controller.fetch_playlist_detail(playlist.uuid)
            self._current_playlist = detail
            self._current_playlist_tracks = tracks
            self.playlist_header.render(detail)
            self.details_stack.setCurrentIndex(2)
            self.playlist_tracks.setVisible(True)
            self.playlist_tracks.load_tracks(tracks)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Playlist Error",
                f"Failed to fetch playlist details:\n{str(e)}"
            )

    @Slot()
    def on_download_playlist(self) -> None:
        if not self._current_playlist or not self._current_playlist_tracks:
            return

        # Create a subdirectory for the playlist
        import re

        # Sanitize playlist title for use as a directory name
        safe_title = re.sub(r'[\\/:*?"<>|]+', '', self._current_playlist.title).strip()
        if not safe_title:
            safe_title = "Playlist"

        playlist_dir = self.controller.download_dir / safe_title

        # Show progress dialog
        dialog = DownloadProgressDialog(total_tracks=len(self._current_playlist_tracks), parent=self)

        # Download tracks in parallel
        def _start(track: Track, completed: int, total: int, worker_id: int) -> None:
            dialog.start_track_safe(track, worker_id)

        def _progress(downloaded: int, total: int, worker_id: int) -> None:
            dialog.report_current_progress_safe(downloaded, total, worker_id)

        def _completed(done: int, total: int, worker_id: int) -> None:
            dialog.track_completed_safe(done, worker_id)

        def _is_cancelled() -> bool:
            return dialog.is_cancelled()

        def _download():
            self.controller.download_tracks_parallel(
                self._current_playlist_tracks,
                playlist_dir,
                DownloadCallbacks(
                    track_started=_start,
                    track_progress=_progress,
                    track_completed=_completed,
                    is_cancelled=_is_cancelled,
                ),
                max_workers=MAX_CONCURRENT_DOWNLOADS,
            )

        # Create worker thread for downloading
        worker = DownloadWorker(_download)
        worker.finished.connect(dialog.accept)

        dialog.show()
        worker.start()
        dialog.exec()  # Block until dialog is closed

    def _refresh_add_button_label(self) -> None:
        target_list = self._active_track_list()
        selected_count = len(target_list.selectedItems())
        self.queue_button.setText(f"Add selected to queue ({selected_count})")


class QueueDialog(QDialog):
    def __init__(
        self,
        controller: AppController,
        download_callback: Callable[[], None],
        queue_changed_callback: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Queue")
        self.setModal(True)
        self._controller = controller
        self._download_callback = download_callback
        self._queue_changed_callback = queue_changed_callback

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._list.setUniformItemSizes(True)
        self._list.setSpacing(0)
        self._refresh_list()

        delete_button = QPushButton("Delete Selected")
        download_button = QPushButton("Download All")
        close_button = QPushButton("Close")

        delete_button.clicked.connect(self._delete_selected)
        download_button.clicked.connect(self._handle_download)
        close_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(delete_button)
        button_layout.addWidget(download_button)
        button_layout.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(button_layout)

    def _refresh_list(self) -> None:
        self._list.clear()
        for track in self._controller.queue_tracks():
            item = QListWidgetItem(_format_queue_entry(track))
            item.setData(Qt.ItemDataRole.UserRole, track)
            self._list.addItem(item)

    def _selected_tracks(self) -> list[Track]:
        selected: list[Track] = []
        for item in self._list.selectedItems():
            track = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(track, Track):
                selected.append(track)
        return selected

    def _delete_selected(self) -> None:
        removed = self._controller.remove_from_queue(self._selected_tracks())
        if removed:
            self._refresh_list()
            self._queue_changed_callback()

    def _handle_download(self) -> None:
        if self._controller.queue_is_empty():
            return
        self._download_callback()
        self._refresh_list()
        self._queue_changed_callback()


class DownloadWorker(QThread):
    """Background thread for downloading tracks."""
    finished = Signal()
    error_occurred = Signal(str)  # Emits error message

    def __init__(self, download_func: Callable[[], None]) -> None:
        super().__init__()
        self._download_func = download_func
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of the download."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled

    def run(self) -> None:
        try:
            self._download_func()
        except Exception as e:
            if not self._cancelled:
                self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()


# noinspection PyUnusedLocal
def report_current_progress(downloaded: int, total: int) -> None:
    QApplication.processEvents()


# noinspection PyUnusedLocal
def start_track(track: Track) -> None:
    QApplication.processEvents()


class DownloadProgressDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, total_tracks: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Downloading...")
        self.setModal(True)
        self._total_tracks = total_tracks
        self._cancelled = False

        # Disable the close button (X)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)

        # Overall progress section
        layout.addWidget(QLabel("Overall Progress"))
        self._total_bar = QProgressBar()
        self._total_bar.setRange(0, total_tracks)
        self._total_bar.setValue(0)
        layout.addWidget(self._total_bar)

        self._total_label = QLabel(f"0 / {total_tracks} downloaded")
        layout.addWidget(self._total_label)

        # Add spacing
        layout.addSpacing(10)

        # Individual worker progress bars
        self._worker_bars: list[QProgressBar] = []
        self._worker_labels: list[QLabel] = []

        for i in range(MAX_CONCURRENT_DOWNLOADS):
            layout.addWidget(QLabel(f"Worker {i + 1}"))

            worker_bar = QProgressBar()
            worker_bar.setRange(0, 1)
            worker_bar.setValue(0)
            self._worker_bars.append(worker_bar)
            layout.addWidget(worker_bar)

            worker_label = QLabel("Idle")
            worker_label.setStyleSheet("color: gray;")
            self._worker_labels.append(worker_label)
            layout.addWidget(worker_label)

            if i < MAX_CONCURRENT_DOWNLOADS - 1:
                layout.addSpacing(5)

        # Cancel button
        layout.addSpacing(10)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(self._cancel_button)

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self._cancelled = True
        self._cancel_button.setEnabled(False)
        self._cancel_button.setText("Cancelling...")
        self.cancel_requested.emit()

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled

    def track_completed(self, completed: int) -> None:
        self._total_bar.setValue(completed)
        self._total_label.setText(f"{completed} / {self._total_tracks} downloaded")
        QApplication.processEvents()

    # Thread-safe versions that use QMetaObject.invokeMethod
    # noinspection PyTypeChecker
    def start_track_safe(self, track: Track, worker_id: int) -> None:
        if 0 <= worker_id < len(self._worker_labels):
            # First reset the progress bar
            QMetaObject.invokeMethod(
                self._worker_bars[worker_id],
                "setMaximum",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, 100)
            )
            QMetaObject.invokeMethod(
                self._worker_bars[worker_id],
                "setValue",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, 0)
            )
            # Then update the label
            QMetaObject.invokeMethod(
                self._worker_labels[worker_id],
                "setText",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, _format_queue_entry(track))
            )

    # noinspection PyTypeChecker
    def report_current_progress_safe(self, downloaded: int, total: int, worker_id: int) -> None:
        if 0 <= worker_id < len(self._worker_bars):
            maximum = max(total, 1)
            QMetaObject.invokeMethod(
                self._worker_bars[worker_id],
                "setMaximum",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, maximum)
            )
            QMetaObject.invokeMethod(
                self._worker_bars[worker_id],
                "setValue",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, min(downloaded, maximum))
            )

    # noinspection PyTypeChecker
    def track_completed_safe(self, completed: int, worker_id: int) -> None:
        # Update overall progress
        QMetaObject.invokeMethod(
            self._total_bar,
            "setValue",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, completed)
        )
        QMetaObject.invokeMethod(
            self._total_label,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, f"{completed} / {self._total_tracks} downloaded")
        )

        # Mark worker as completed (will show 100% progress bar)
        if 0 <= worker_id < len(self._worker_bars):
            QMetaObject.invokeMethod(
                self._worker_bars[worker_id],
                "setValue",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, self._worker_bars[worker_id].maximum())
            )

        # If cancellation was requested, show "Waiting..." for this worker
        if self._cancelled and 0 <= worker_id < len(self._worker_labels):
            QMetaObject.invokeMethod(
                self._worker_labels[worker_id],
                "setText",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, "Waiting for other thread(s)...")
            )
        # If all tracks are done, mark workers as completed
        elif completed >= self._total_tracks:
            for i in range(len(self._worker_labels)):
                QMetaObject.invokeMethod(
                    self._worker_labels[i],
                    "setText",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, "Completed")
                )


class PlaylistHeaderWidget(QWidget):
    download_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self._cover = QLabel()
        self._cover.setFixedSize(160, 160)
        layout.addWidget(self._cover)

        text_container = QVBoxLayout()
        text_container.setSpacing(4)

        # hack: set text container to wrap on vertical height so that the cover and text align at top
        text_container.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._title = QLabel("Select a playlist")
        self._title.setWordWrap(True)
        self._title.setStyleSheet("font-weight: bold; font-size: 18pt;")

        self._meta = QLabel()
        self._meta.setStyleSheet("color: gray;")

        self._desc = QLabel()
        self._desc.setWordWrap(True)

        self._download_button = QPushButton("Download Playlist")
        self._download_button.clicked.connect(self.download_requested.emit)

        text_container.addWidget(self._title)
        text_container.addWidget(self._meta)
        text_container.addWidget(self._desc)
        text_container.addWidget(self._download_button)
        layout.addLayout(text_container)

    def render(self, playlist: Playlist, **kwargs) -> None:
        pixmap = load_cover_pixmap(playlist.cover_id, 640, 160)
        self._cover.setPixmap(pixmap)
        self._title.setText(playlist.title)
        duration = format_duration(playlist.duration, long=True)
        artists = ", ".join(playlist.featured_artists) if playlist.featured_artists else "various"
        self._meta.setText(f"{playlist.number_of_tracks} tracks • {duration} • {artists}")
        self._desc.setText(playlist.description or "no description")

