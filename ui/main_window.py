from __future__ import annotations

from typing import Callable
import re
import time

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
    QWidget, QLayout,
)

from config import MAX_CONCURRENT_DOWNLOADS
from controllers.app_controller import AppController, DownloadCallbacks
from models.album import Album
from models.playlist import Playlist
from models.track import Track
from utils.formatting import format_track_listing
from widgets.album_list_widget import AlbumListWidget
from widgets.header_widget import AlbumHeaderWidget, PlaylistHeaderWidget
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
        self._current_album: Album | None = None
        self._current_album_tracks: list[Track] = []

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
        self.album_list = AlbumListWidget()

        self.playlist_header = PlaylistHeaderWidget()
        self.playlist_tracks = TrackListWidget()
        playlist_page = QWidget()
        self.playlist_page = playlist_page
        playlist_layout = QVBoxLayout(playlist_page)
        playlist_layout.setContentsMargins(0, 0, 0, 0)
        playlist_layout.setSpacing(8)
        playlist_layout.addWidget(self.playlist_header)
        playlist_layout.addWidget(self.playlist_tracks)

        self.album_header = AlbumHeaderWidget()
        self.album_tracks = TrackListWidget()
        album_page = QWidget()
        self.album_page = album_page
        album_layout = QVBoxLayout(album_page)
        album_layout.setContentsMargins(0, 0, 0, 0)
        album_layout.setSpacing(8)
        album_layout.addWidget(self.album_header)
        album_layout.addWidget(self.album_tracks)

        self.details_stack = QStackedWidget()
        self.details_stack.addWidget(self.track_list)
        self.details_stack.addWidget(self.playlist_list)
        self.details_stack.addWidget(playlist_page)
        self.details_stack.addWidget(self.album_list)
        self.details_stack.addWidget(album_page)
        self.details_stack.setCurrentWidget(self.track_list)

        self.notice_label = QLabel("Cannot search this type yet, please try Tracks, Albums, or Playlists.")
        self.notice_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notice_label.setVisible(False)

        root_layout = QVBoxLayout(self)
        root_layout.addLayout(top_layout)
        root_layout.addWidget(self.details_stack)
        root_layout.addWidget(self.notice_label)

        self.playlist_list.playlist_activated.connect(self.on_playlist_selected)
        self.playlist_header.download_requested.connect(self.on_download_playlist)
        self.album_list.album_activated.connect(self.on_album_selected)
        self.album_header.download_requested.connect(self.on_download_album)
        self.search_button.clicked.connect(self.on_search_clicked)
        self.queue_button.clicked.connect(self.on_queue_selected)
        self.show_queue_button.clicked.connect(self.on_show_queue)
        self.track_list.itemSelectionChanged.connect(self._refresh_add_button_label)
        self.playlist_tracks.itemSelectionChanged.connect(self._refresh_add_button_label)
        self.album_tracks.itemSelectionChanged.connect(self._refresh_add_button_label)
        self._refresh_add_button_label()
        self._update_queue_label()

    def _active_track_list(self) -> TrackListWidget:
        current_widget = self.details_stack.currentWidget()
        if current_widget is self.track_list:
            return self.track_list
        if current_widget is self.playlist_page:
            return self.playlist_tracks
        if current_widget is self.album_page:
            return self.album_tracks
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
            elif category == "Albums":
                self.notice_label.hide()
                self.details_stack.setCurrentWidget(self.album_list)
                self.album_list.load_albums(results)
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

    def _download_tracks_with_progress(
        self,
        tracks: list[Track],
        title: str,
        default_title: str = "Download"
    ) -> None:
        """Download tracks with a progress dialog."""
        safe_title = re.sub(r'[\\/:*?"<>|]+', '', title).strip()
        if not safe_title:
            safe_title = default_title

        download_dir = self.controller.download_dir / safe_title

        dialog = DownloadProgressDialog(total_tracks=len(tracks), parent=self)

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
                tracks,
                download_dir,
                DownloadCallbacks(
                    track_started=_start,
                    track_progress=_progress,
                    track_completed=_completed,
                    is_cancelled=_is_cancelled,
                ),
                max_workers=MAX_CONCURRENT_DOWNLOADS,
            )

        worker = DownloadWorker(_download)
        worker.finished.connect(dialog.accept)

        dialog.show()
        worker.start()
        dialog.exec()

    @Slot()
    def on_download_playlist(self) -> None:
        if not self._current_playlist or not self._current_playlist_tracks:
            return
        self._download_tracks_with_progress(
            self._current_playlist_tracks,
            self._current_playlist.title,
            "Playlist"
        )

    @Slot(Album)
    def on_album_selected(self, album: Album) -> None:
        try:
            detail, tracks = self.controller.fetch_album_detail(album.album_id)
            self._current_album = detail
            self._current_album_tracks = tracks
            self.album_header.render(detail)
            self.details_stack.setCurrentWidget(self.album_page)
            self.album_tracks.setVisible(True)
            self.album_tracks.load_tracks(tracks)
        except Exception as e:
            print(e)
            QMessageBox.critical(
                self,
                "Album Error",
                f"Failed to fetch album details:\n{str(e)}"
            )

    @Slot()
    def on_download_album(self) -> None:
        if not self._current_album or not self._current_album_tracks:
            return
        self._download_tracks_with_progress(
            self._current_album_tracks,
            self._current_album.title,
            "Album"
        )

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
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, download_func: Callable[[], None]) -> None:
        super().__init__()
        self._download_func = download_func
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def is_cancelled(self) -> bool:
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


class WorkerProgressWidget(QWidget):
    def __init__(self, worker_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker_id = worker_id
        self._last_progress = 0
        self._last_maximum = 1
        self._last_update_time = 0.0
        self._last_bytes = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._title_label = QLabel(f"Worker {worker_id + 1}")
        self._title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._title_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 1)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        self._track_label = QLabel("Idle")
        self._track_label.setStyleSheet("color: gray;")
        # Ensure the label can expand horizontally
        self._track_label.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Maximum
        )
        layout.addWidget(self._track_label)

        self._speed_label = QLabel("")
        self._speed_label.setStyleSheet("color: #666; font-size: 10pt;")
        layout.addWidget(self._speed_label)

        self.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Maximum
        )
        layout.setSizeConstraint(
            QLayout.SizeConstraint.SetFixedSize
        )

    @Slot(str)
    def set_track(self, track_text: str) -> None:
        self._track_label.setText(track_text)
        self._track_label.setStyleSheet("")
        self._last_progress = 0
        self._last_maximum = 100
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._last_update_time = time.time()
        self._last_bytes = 0
        self._speed_label.setText("")

    @Slot(int, int)
    def set_progress(self, current: int, maximum: int) -> None:
        maximum = max(maximum, 1)
        current = min(current, maximum)

        if current > self._last_progress or maximum != self._last_maximum:
            self._last_progress = current
            self._last_maximum = maximum
            self._progress_bar.setMaximum(maximum)
            self._progress_bar.setValue(current)

            # Calculate download speed
            current_time = time.time()
            time_diff = current_time - self._last_update_time

            # Update speed every 0.5 seconds to avoid too frequent updates
            if time_diff >= 0.5 and current > self._last_bytes:
                bytes_diff = current - self._last_bytes
                speed_bps = bytes_diff / time_diff  # bytes per second
                speed_mbps = speed_bps / (1024 * 1024)  # convert to MB/s

                self._speed_label.setText(f"{speed_mbps:.2f} MB/s")

                self._last_update_time = current_time
                self._last_bytes = current

    @Slot()
    def set_idle(self) -> None:
        self._track_label.setText("Idle")
        self._track_label.setStyleSheet("color: gray;")
        self._progress_bar.setValue(0)
        self._speed_label.setText("")

    @Slot()
    def set_completed(self) -> None:
        self._track_label.setText("Completed")
        self._track_label.setStyleSheet("color: green;")
        self._progress_bar.setValue(self._progress_bar.maximum())
        self._speed_label.setText("")

    @Slot()
    def set_waiting(self) -> None:
        self._track_label.setText("Waiting for other thread(s)...")
        self._track_label.setStyleSheet("color: orange;")
        self._speed_label.setText("")


class DownloadProgressDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, total_tracks: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Download Progress")
        self.setModal(True)
        self._total_tracks = total_tracks
        self._cancelled = False
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed
        )

        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)

        # Overall progress section
        overall_label = QLabel("Overall Progress")
        overall_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(overall_label)

        self._total_bar = QProgressBar()
        self._total_bar.setRange(0, total_tracks)
        self._total_bar.setValue(0)
        layout.addWidget(self._total_bar)

        self._total_label = QLabel(f"0 / {total_tracks} downloaded")
        layout.addWidget(self._total_label)

        layout.addSpacing(16)

        # Worker progress widgets
        self._workers: list[WorkerProgressWidget] = []
        for i in range(MAX_CONCURRENT_DOWNLOADS):
            worker_widget = WorkerProgressWidget(i, self)
            self._workers.append(worker_widget)
            layout.addWidget(worker_widget)

            # after adding each worker, we need to trigger a layout update so that the dialog resizes properly
            layout.update()
            self.layout().update()

            if i < MAX_CONCURRENT_DOWNLOADS - 1:
                layout.addSpacing(8)

            self.adjustSize()

            layout.activate()
            self.layout().activate()

        # Cancel button
        layout.addSpacing(16)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(self._cancel_button)

        layout.update()
        self.layout().update()

        self.adjustSize()

    def _on_cancel_clicked(self) -> None:
        self._cancelled = True
        self._cancel_button.setEnabled(False)
        self._cancel_button.setText("Cancelling...")
        self.cancel_requested.emit()

    def is_cancelled(self) -> bool:
        return self._cancelled

    # noinspection PyTypeChecker
    def start_track_safe(self, track: Track, worker_id: int) -> None:
        if 0 <= worker_id < len(self._workers):
            track_text = _format_queue_entry(track)
            QMetaObject.invokeMethod(
                self._workers[worker_id],
                "set_track",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, track_text)
            )

    # noinspection PyTypeChecker
    def report_current_progress_safe(self, downloaded: int, total: int, worker_id: int) -> None:
        if 0 <= worker_id < len(self._workers):
            QMetaObject.invokeMethod(
                self._workers[worker_id],
                "set_progress",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, downloaded),
                Q_ARG(int, total)
            )

    # noinspection PyTypeChecker
    def track_completed_safe(self, completed: int, worker_id: int) -> None:
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

        if 0 <= worker_id < len(self._workers):
            if self._cancelled:
                QMetaObject.invokeMethod(
                    self._workers[worker_id],
                    "set_waiting",
                    Qt.ConnectionType.QueuedConnection
                )
            elif completed >= self._total_tracks:
                QMetaObject.invokeMethod(
                    self._workers[worker_id],
                    "set_completed",
                    Qt.ConnectionType.QueuedConnection
                )
            else:
                QMetaObject.invokeMethod(
                    self._workers[worker_id],
                    "set_idle",
                    Qt.ConnectionType.QueuedConnection
                )

        if completed >= self._total_tracks:
            for i, worker in enumerate(self._workers):
                QMetaObject.invokeMethod(
                    worker,
                    "set_completed",
                    Qt.ConnectionType.QueuedConnection
                )



