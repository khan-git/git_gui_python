import json
import os
import sys
import json
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from datetime import datetime

from git import Repo, Head, RemoteProgress, GitCommandError

class Cache():
    def __init__(self) -> None:
        pass


class GroupItem(QStandardItem):
    def __init__(self, text: str):
        super().__init__(text)

class RepoItem(QStandardItem):
    def __init__(self, text: str, repo: Repo):
        super().__init__(text)
        self.setData(repo, Qt.UserRole)
        self.path_item = QStandardItem(repo.working_dir)
        self.branch_name = QStandardItem(repo.active_branch.name)

    @property
    def items(self) -> list:
        return [self, self.branch_name, self.path_item]
    
    @property
    def repo(self) -> Repo:
        return self.data(Qt.UserRole)
    
    @property
    def branches(self) -> list:
        """Returns a list of Head"""
        return self.repo.branches

    def create_branch(self, branch: str) -> Head:
        """Create branch. Validate if already exists"""
        if branch in self.repo.branches:
            return self.branches
        return self.repo.create_head(branch)

    @property
    def current_branch(self) -> Head:
        return self.repo.head
        
    def get_branch(self, branch) -> Head:
        for b in self.repo.branches:
            if branch == b.name:
                return b
        return None
    
    def set_branch(self, branch, create_if_not_existing: bool = False) -> Head:
        """Set branch if exists. Create  if told so.
        Return None if branch does not exist"""
        repo: Repo = self.repo
        if branch not in repo.heads and create_if_not_existing:
            new_branch: Head = self.create_branch(branch)
            print(f'{new_branch.name} created in {self.text()}')
        if branch in repo.heads:
            branch_to_set: Head = self.get_branch(branch)
            try:
                branch_to_set.checkout()
                self.branch_name.setText(self.repo.active_branch.name)
            except GitCommandError as ex:
                QMessageBox.information(None, f"Git Error: {self.text()}", ex.stderr)
            return self.repo.head
        else:
            return None
        
    def update_dirty_status(self):
        if self.repo.is_dirty():
            self.setForeground(QColorConstants.DarkYellow)
            self.setIcon(qApp.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
            self.setToolTip("Dirty!")
        else:
            self.setForeground(QColorConstants.Black)
            self.setToolTip("")

        
    def pull(self):
        repo: Repo = self.repo
        if 'origin' in repo.remotes:
            try:
                repo.remotes.origin.pull()
            except GitCommandError as ex:
                QMessageBox.information(None, f"Git Error: {self.text()}", ex.stderr)


class MyProgressPrinter(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=""):
        print(
            op_code,
            cur_count,
            max_count,
            cur_count / (max_count or 100.0),
            message or "NO MESSAGE",
        )

class AddToGroupDialog(QDialog):

    def __init__(self, parent: QWidget | None, groups: []) -> None:

        super().__init__(parent)
        self.setWindowTitle("Add to group")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.group_boxes = []
        groups_box_label = QLabel("Groups: ", parent)
        self.layout.addWidget(groups_box_label)
        for group in groups:
            gCB = QCheckBox(group, parent)
            self.group_boxes.append(gCB)
            self.layout.addWidget(gCB)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)


class SelectBranchDialog(QDialog):

    def __init__(self, parent: QWidget | None, branches: []) -> None:

        super().__init__(parent)
        self.setWindowTitle("Select branch")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.branch_combo = QComboBox()
        self.branch_combo.addItems(branches)
        self.addAction

        self.force = QCheckBox("Force")

        form_layout = QFormLayout()
        form_layout.addRow("Branches:", self.branch_combo)
        self.layout.addLayout(form_layout)

        self.layout.addWidget(self.force)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.settings = QSettings("GitGui", "GitGui")
        self._repositories: dict = json.loads(self.settings.value('repositories', '{}'))
        self._groups: dict = json.loads(self.settings.value('groups', '{}'))
        self._groups_expanded: [] = json.loads(self.settings.value('groups_expanded', '[]'))
        print(f'Settings file: {self.settings.fileName()}')

        self.setMinimumSize(800, 900)

        # Move window to center of screen and slightly up
        qr = self.frameGeometry()
        cp:QPoint = self.screen().availableGeometry().center()
#        cp.setY(int(cp.y()/2))
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        self.window_title = "Git Gui"
        self.setWindowTitle(self.window_title)
        
        self.status_bar = self.statusBar()
        self.setupMenuBar()
        cWidget = QWidget()
        centralLayout = QHBoxLayout()
        cWidget.setLayout(centralLayout)
        
        centralLayout.addWidget(self.createRepositoryTable())
        self.setCentralWidget(cWidget)
        self.update_repository_data()

        # self.setFocusPolicy(Qt.StrongFocus)
        # self._dirty_timer = QTimer(self)
        # self._dirty_timer.timeout.connect(self.update_dirty_status)
        # self._dirty_timer.start(5000)
 
    def focusInEvent(self, e):
        self._dirty_timer.stop()
        print("Set timer 5s")
        self.update_dirty_status()
        self._dirty_timer.setInterval(5000)
        self._dirty_timer.start()
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        self._dirty_timer.stop()
        print("Set timer 15s")
        self._dirty_timer.setInterval(15000)
        self._dirty_timer.start()
        super().focusOutEvent(e)

    @pyqtSlot()
    def start_dirty_timer(self):
        self._dirty_timer = QTimer(self)
        self._dirty_timer.timeout.connect(self.update_dirty_status)
        self._dirty_timer.start(20000)

    @pyqtSlot(QModelIndex)
    def dlblSelected(self, newIndex: QModelIndex):
        item: QListWidgetItem = self.dlblList.itemFromIndex(newIndex)
        print(item.data(Qt.UserRole))
                
    def createRepositoryTable(self):
        box = QGroupBox("Git repositories")
        bl = QHBoxLayout()
        box.setLayout(bl)
        self.repositoryTreeModel = QStandardItemModel(0, 3 , self)
        self.repositoryTreeModel.setHeaderData(0, Qt.Horizontal, "Group")
        self.repositoryTreeModel.setHeaderData(1, Qt.Horizontal, "Branch")
#        self.treeModel.setHeaderData(2, Qt.Horizontal, "Repository")
        self._group_all = QStandardItem('All')
        self.repositoryTreeModel.invisibleRootItem().appendRow([self._group_all])


        self.repositoryTree = QTreeView()
        self.repositoryTree.setModel(self.repositoryTreeModel)
        self.repositoryTree.setAnimated(False)
        self.repositoryTree.setIndentation(20)
        self.repositoryTree.setSortingEnabled(True)
        self.repositoryTree.setWindowTitle("Dir View")
        self.repositoryTree.resize(640, 480)
        self.repositoryTree.setColumnWidth(1, 300)
        self.repositoryTree.resizeColumnToContents(0)
        self.repositoryTree.resizeColumnToContents(1)
#        self.repositoryTree.resizeColumnToContents(2)
        self.repositoryTree.hideColumn(2)
        self.repositoryTree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.repositoryTree.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)


        self.repositoryTree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.repositoryTree.customContextMenuRequested.connect(self.rightMouseMenu)

        self.repositoryTree.expanded.connect(self.adjustTreeColumns)
        self.repositoryTree.collapsed.connect(self.save_tree_expand)
        bl.addWidget(self.repositoryTree)
        return box

    def rightMouseMenu(self, position: QPoint):
        cIndex: QModelIndex = self.repositoryTree.currentIndex()
        item = self.repositoryTreeModel.itemFromIndex(cIndex.siblingAtColumn(0))

        menu = QMenu()
        items: list = self.items_from_indexes(self.repositoryTree.selectedIndexes(), self.repositoryTreeModel)
        if type(item) is RepoItem:
            # Repository menu
            pIndex = self.repositoryTree.indexAt(position)
            pytest_xml: str = pIndex.siblingAtColumn(0).data(Qt.ItemDataRole.UserRole)

            menu = QMenu()
            action:QAction = menu.addAction("Set to branch")
            action.triggered.connect(lambda: self.set_to_branch(items))
            action:QAction = menu.addAction("Pull")
            action.triggered.connect(lambda: self.do_pull(items))
            menu.addSeparator()
            action:QAction = menu.addAction("Create branch")
            action.triggered.connect(lambda: self.create_branch(items))
            menu.addSeparator()
            action:QAction = menu.addAction("Add to group")
            action.triggered.connect(lambda: self.add_to_group(items))

        if type(item) is GroupItem:
            # Group menus
            if item.text() == "All":
                return

            menu = QMenu()
            action:QAction = menu.addAction("Set to branch")
            action.triggered.connect(lambda: self.set_to_branch(items))
            action:QAction = menu.addAction("Create branch")
            action.triggered.connect(lambda: self.create_branch(items))
            action:QAction = menu.addAction("Pull")
            action.triggered.connect(lambda: self.do_pull(items))
            menu.addSeparator()
            action:QAction = menu.addAction("Rename group")
            action.triggered.connect(self.rename_group)
            action:QAction = menu.addAction("Remove group")
            action.triggered.connect(self.remove_group)
                    
        menu.exec(self.repositoryTree.viewport().mapToGlobal(position))

    def rename_group(self):
        cIndex: QModelIndex = self.repositoryTree.currentIndex()
        item = self.repositoryTreeModel.itemFromIndex(cIndex.siblingAtColumn(0))
        group_name, ok = QInputDialog.getText(self, 'Rename group', 'New name:')
        if ok and group_name:
            data = self._groups.pop(item.text())
            item.setText(group_name)
            self._groups[group_name] = data
            self.save_groups_to_settings()
            self.update_repository_data()
        

    def remove_group(self):
        cIndex: QModelIndex = self.repositoryTree.currentIndex()
        item = self.repositoryTreeModel.itemFromIndex(cIndex.siblingAtColumn(0))
        answere = QMessageBox.critical(self, "Remove group", f"Do you wish to remove group {item.text()}?", buttons=QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                             defaultButton=QMessageBox.StandardButton.No)
        if answere == QMessageBox.StandardButton.Yes:
            if item.text() in self._groups:
                self._groups.pop(item.text())
                self.update_repository_data()

    def items_from_indexes(self, indexes: list, tree_model: QStandardItemModel) -> list:
        items = []
        rows = []
        index: QModelIndex
        for index in indexes:
            if index.row() not in rows:
                items.append(tree_model.itemFromIndex(index.siblingAtColumn(0)))
                rows.append(index.row())
        return items

    def add_to_group(self, items: list):
        dcd = AddToGroupDialog(self, self._groups.keys())
        if dcd.exec():
            group_box: QCheckBox
            for group_box in dcd.group_boxes:
                if group_box.isChecked():
                    if group_box.text() in self._groups.keys():
                        group_meta: [] = self._groups.get(group_box.text())
                        for item in items:
                            group_meta.append(item.text())
                        self._groups[group_box.text()] = group_meta
            self.save_groups_to_settings()
            self.update_repository_data()
        else:
            # Cancel selected
            return

    def create_branch(self, items: list):
        """Open dialog to get branch name, check if already exist and then create.
        Have a set-checkbox to set immediately."""
        branch_name, ok = QInputDialog.getText(self, 'Create branch dialog', 'Branch:')
        if not ok or not branch_name:
            return

        for item in items:
            if type(item) is RepoItem:
                self._create_branch(item, branch_name)
            if type(item) is GroupItem:
                print(f"Group item {item.text()}")
                for row in range(item.rowCount()):
                    child: RepoItem = item.child(row, 0)
                    self._create_branch(child, branch_name)

    def do_pull(self, items: list):
        """Pull on all selected repos"""
        for item in items:
            if type(item) is RepoItem:
                item.pull()
            if type(item) is GroupItem:
                for row in range(item.rowCount()):
                    child: RepoItem = item.child(row, 0)
                    child.pull()

    def _create_branch(self, item: RepoItem, branch_name: str):
        """Check existence of branch before creating it in Repo"""
        if branch_name in item.branches:
            print(f"{branch_name} exists in {item.text()}")
        elif item.create_branch(branch_name):
            print(f"Branch {branch_name} created in {item.text()}")


    def set_to_branch(self, items: list):
        """Set all repos in group to branch"""
        heads = []
        branch_names = []

        for item in items:
            if type(item) is RepoItem:
                heads.extend(item.branches)
            elif type(item) is GroupItem:
                for row in range(item.rowCount()):
                    child: RepoItem = item.child(row, 0)
                    heads.extend(child.branches)
                    
        # Get branch names from Heads
        br: Head
        for br in heads:
            if br.name not in branch_names:
                branch_names.append(br.name)

        sbd = SelectBranchDialog(self, branch_names)
        if sbd.exec():
            branch_name: str = sbd.branch_combo.currentText()
            force: bool = sbd.force.isChecked()
            for item in items:
                if type(item) is RepoItem:
                    item.set_branch(branch_name, create_if_not_existing=force)
                elif type(item) is GroupItem:
                    for row in range(item.rowCount()):
                        child: RepoItem = item.child(row, 0)
                        child.set_branch(branch_name, create_if_not_existing=force)
            # self.update_repository_data()
        else:
            # Cancel selected
            return

    @pyqtSlot()
    def adjustTreeColumns(self):
        self.repositoryTree.resizeColumnToContents(1)
        self.save_tree_expand()
        
    def save_tree_expand(self):
        self._groups_expanded = []
        root: QStandardItem = self.repositoryTreeModel.invisibleRootItem()
        for row in range(root.rowCount()):
            item: GroupItem = root.child(row, column=0)
            if type(item) is GroupItem:
                if self.repositoryTree.isExpanded(self.repositoryTreeModel.indexFromItem(item)):
                    self._groups_expanded.append(item.text())
        self.settings.setValue('groups_expanded', json.dumps(self._groups_expanded))

    def setupMenuBar(self):
        """Set up menu bar with all options"""
        quitAction = QAction("&Quit", self)
        quitAction.setShortcut("Ctrl+Q")
        quitAction.setStatusTip('Terminate application')
        quitAction.triggered.connect(sys.exit)

        reloadAction = QAction("&Update", self)
        reloadAction.setShortcut("Ctrl+R")
        reloadAction.setStatusTip('Read all git repos')
        reloadAction.triggered.connect(self.update_repository_data)
        
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(reloadAction)
        fileMenu.addAction(quitAction)

        infoAction = QAction("&Info", self)
        infoAction.setStatusTip('Information about application')
        infoAction.triggered.connect(self.info_dialog)

        fileMenu = mainMenu.addMenu('&Settings')

        addRepositoryAction = QAction("&Add repository", self)
        addRepositoryAction.setStatusTip('Add git repository path')
        addRepositoryAction.triggered.connect(self.addRepository)
        fileMenu.addAction(addRepositoryAction)

        addGroupAction = QAction("&Create group", self)
        addGroupAction.setStatusTip('Create group')
        addGroupAction.triggered.connect(self.createGroup)
        fileMenu.addAction(addGroupAction)

        fileMenu = mainMenu.addMenu('&About')
        fileMenu.addAction(infoAction)

    @pyqtSlot()
    def info_dialog(self):
        box = QMessageBox.information(self, "About", "Disclaimer!!\nUse at your own peril!")

    @pyqtSlot()
    def createGroup(self):
        text, ok = QInputDialog.getText(self, 'Create group', 'Group name:')
        if ok:
            rootItem = self.repositoryTreeModel.invisibleRootItem()
            groupItem = QStandardItem(text)
            rootItem.appendRow([groupItem])
            self._groups[text] = ["empty"]
            self.settings.setValue('groups', json.dumps(self._groups))
            self.update_repository_data()


    @pyqtSlot()
    def addRepository(self, group: str = "All"):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.DirectoryOnly)
        file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        file_view = file_dialog.findChild(QListView, 'listView')

        # to make it possible to select multiple directories:
        if file_view:
            file_view.setSelectionMode(QAbstractItemView.MultiSelection)
        f_tree_view = file_dialog.findChild(QTreeView)
        if f_tree_view:
            f_tree_view.setSelectionMode(QAbstractItemView.MultiSelection)

        if file_dialog.exec():
            paths = file_dialog.selectedFiles()
            for repository_path in paths:
                if os.path.exists(repository_path):
                    try:
                        self._repositories[os.path.basename(repository_path)] = {'path': repository_path, 'repo': Repo(repository_path)}
                    except Exception as e:
                        print(f'{repository_path}: {e}')
            self.save_repositories_to_settings()
            self.update_repository_data()

    def save_repositories_to_settings(self):
        """Save repo data to JSON"""
        save_json = {}
        value: dict
        for key, value in self._repositories.items():
            save_json[key] = {'path': value.get('path')}
        self.settings.setValue('repositories', json.dumps(save_json))

    def save_groups_to_settings(self):
        """Save group data to JSON"""
        self.settings.setValue('groups', json.dumps(self._groups))

    def add_to_tree(self, name: str, repo: Repo, group: GroupItem):
        repo_item = RepoItem(name, repo)
        group.appendRow(repo_item.items)
        self.repositoryTree.setSortingEnabled(True)
        # self.repositoryTree.expandAll()
        self.repositoryTree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        for c in range(0, self.repositoryTreeModel.columnCount()):
            self.repositoryTree.resizeColumnToContents(c)
                    
    @pyqtSlot()
    def update_repository_data(self):
        self.repositoryTree.expanded.disconnect(self.adjustTreeColumns)
        self.repositoryTree.collapsed.disconnect(self.save_tree_expand)

        self.repositoryTreeModel.setRowCount(0)

        self._group_all = GroupItem('All')
        value: dict
        for name in sorted(self._repositories.keys()):
            value: dict = self._repositories.get(name)
            repo: Repo
            if 'path' not in value or not os.path.exists(value.get('path')):
                continue
            
            if 'repo' in value:
                repo = value.get('repo')
            else:
                repo = Repo(value.get('path'))
                value['repo'] = repo
            self.add_to_tree(name, repo, self._group_all)

        for group, value in self._groups.items():
            group_item = GroupItem(group)
            self.repositoryTreeModel.invisibleRootItem().appendRow([group_item])
            for val in value:
                data = self._repositories.get(val)
                if data is not None and 'repo' in data:
                    self.add_to_tree(val, data['repo'], group_item)

            if group in self._groups_expanded:
                g_index = self.repositoryTreeModel.indexFromItem(group_item)
                self.repositoryTree.expand(g_index)

        self.repositoryTreeModel.invisibleRootItem().appendRow([self._group_all])
        if 'All' in self._groups_expanded:
            g_index = self.repositoryTreeModel.indexFromItem(self._group_all)
            self.repositoryTree.expand(g_index)

        self.repositoryTree.expanded.connect(self.adjustTreeColumns)
        self.repositoryTree.collapsed.connect(self.save_tree_expand)

        QTimer.singleShot(10, self.update_dirty_status)


    @pyqtSlot()
    def update_dirty_status(self):
        """Uppdate background color if dirty"""
        curr_time: datetime = datetime.now()
        child: RepoItem
        for group_row in range(self.repositoryTreeModel.invisibleRootItem().rowCount()):
            group_item = self.repositoryTreeModel.invisibleRootItem().child(group_row)
            for child_row in range(group_item.rowCount()):
                child = group_item.child(child_row)
                child.update_dirty_status()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
