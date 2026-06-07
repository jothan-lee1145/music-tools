import tkinter as tk
from tkinter import ttk
from config import setup_proxy
from tagger import TaggerModule
from downloader import DownloaderModule
from converter import ConverterModule
from lyrics import LyricsModule


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("音乐工具箱")
        self.root.geometry("940x660")

        self.status1 = tk.StringVar(value="初始化中...")
        self.status2 = tk.StringVar(value="初始化中...")
        self.status3 = tk.StringVar(value="初始化中...")
        self.status4 = tk.StringVar(value="初始化中...")

        setup_proxy()
        self.root.after(100, lambda: [self.status1.set("就绪"), self.status2.set("就绪"),
                                      self.status3.set("就绪"), self.status4.set("就绪")])

        self._build_ui()

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="标签嵌入")
        self.tagger = TaggerModule(self.root, self.status1)
        self.tagger.create_ui(tab1)
        ttk.Label(tab1, textvariable=self.status1, relief='sunken', anchor='w').pack(fill='x', padx=10, pady=5)

        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="音乐下载")
        self.downloader = DownloaderModule(self.root, self.status2, lambda path, data: self._trigger_tagger(path, data))
        self.downloader.create_ui(tab2)
        ttk.Label(tab2, textvariable=self.status2, relief='sunken', anchor='w').pack(fill='x', padx=10, pady=5)

        tab3 = ttk.Frame(notebook)
        notebook.add(tab3, text="格式转换")
        self.converter = ConverterModule(self.root, self.status3)
        self.converter.create_ui(tab3)

        tab4 = ttk.Frame(notebook)
        notebook.add(tab4, text="歌词嵌入")
        self.lyrics = LyricsModule(self.root, self.status4)
        self.lyrics.create_ui(tab4)
        ttk.Label(tab4, textvariable=self.status4, relief='sunken', anchor='w').pack(fill='x', padx=10, pady=5)

    def _trigger_tagger(self, file_path, download_data):
        self.tagger.selected_file = file_path
        self.tagger.selected_result = {
            'trackName': download_data['name'], 'artistName': download_data['artist'],
            'collectionName': download_data['album'], 'trackNumber': '',
            'artworkUrl': '', 'pic_id': download_data.get('pic_id', ''),
            'source_name': download_data['source'], 'source': 'GDStudio'
        }
        self.tagger._apply_worker()


if __name__ == "__main__":
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()