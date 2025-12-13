from __future__ import annotations

from PySide6.QtWidgets import QListWidget


class BaseListWidget(QListWidget):
    """Base class for list widgets with common selection sync logic."""

    def __init__(self) -> None:
        super().__init__()
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setUniformItemSizes(False)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)

        # set all margins and spacing to 0
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

    def selectionChanged(self, selected, deselected) -> None:
        super().selectionChanged(selected, deselected)
        self._sync_item_widget_selection()

    def _sync_item_widget_selection(self) -> None:
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if widget and hasattr(widget, "set_selected_state"):
                widget.set_selected_state(item.isSelected())

