import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import mutagen
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC, Picture
import mutagen.mp4, mutagen.mp3
import re, threading, os, tempfile, subprocess
from urllib.parse import quote
from PIL import Image, ImageTk
from config import session, API_BASE, REGIONS


class TaggerModule:
    def __init__(self, root, status_var):
        self.root = root
        self.status_var = status_var
        self.results_data = []
        self.selected_result = None
        self.selected_file = None
        self.cover_tk = None
        self.preview_labels = {}

    def create_ui(self, parent):
        ctrl = ttk.Frame(parent);
        ctrl.pack(pady=8, padx=10, fill='x')
        ttk.Label(ctrl, text="查询词:").grid(row=0, column=0, padx=(0, 5), sticky='w')
        self.entry = ttk.Entry(ctrl, width=30);
        self.entry.grid(row=0, column=1, padx=5)
        self.entry.bind("<Return>", lambda e: self.search())

        ttk.Label(ctrl, text="区域:").grid(row=0, column=2, padx=(10, 5), sticky='w')
        self.region_var = tk.StringVar(value="🇨 中国大陆 (CN)")
        rc = ttk.Combobox(ctrl, textvariable=self.region_var, state="readonly", width=18, values=list(REGIONS.keys()))
        rc.grid(row=0, column=3, padx=5);
        rc.current(0)
        ttk.Button(ctrl, text="搜索", command=self.search).grid(row=0, column=4, padx=5)

        mid = ttk.Frame(parent);
        mid.pack(pady=5, padx=10, fill='both', expand=True)
        left = ttk.Frame(mid);
        left.pack(side='left', fill='both', expand=True, padx=(0, 5))
        cols = ("song", "artist", "album", "year")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=10)
        for c, t in zip(cols, ["歌曲", "艺术家", "专辑", "年份"]): self.tree.heading(c, text=t)
        self.tree.column("song", width=180);
        self.tree.column("artist", width=100)
        self.tree.column("album", width=140);
        self.tree.column("year", width=60, anchor='center')
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set);
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill='both', expand=True);
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        right = ttk.LabelFrame(mid, text="预览", width=240);
        right.pack(side='right', fill='y', padx=(5, 0))
        right.pack_propagate(False)
        self.canvas = tk.Canvas(right, width=200, height=200, bg="#e8e8e8", highlightthickness=1)
        self.canvas.pack(pady=10)
        self.cover_lbl = ttk.Label(right, text="请选择结果", foreground="gray", wraplength=180)
        self.cover_lbl.pack(pady=5)
        info = ttk.Frame(right);
        info.pack(pady=10, padx=10, fill='x')
        for key in ["歌曲", "艺术家", "专辑", "轨号", " 年份", "数据源"]:
            ttk.Label(info, text=key, font=("Microsoft YaHei", 9)).pack(anchor='w', pady=(4, 0))
            lbl = ttk.Label(info, text="-", wraplength=200, font=("Consolas", 9))
            lbl.pack(anchor='w', pady=(0, 6));
            self.preview_labels[key] = lbl

        ff = ttk.Frame(parent);
        ff.pack(pady=5, padx=10, fill='x')
        ttk.Button(ff, text="选择文件", command=self.select_file).pack(side='left')
        self.file_lbl = ttk.Label(ff, text="未选择", foreground="gray");
        self.file_lbl.pack(side='left', padx=10)
        bf = ttk.Frame(parent);
        bf.pack(pady=8)
        self.preview_btn = ttk.Button(bf, text="试听", command=self.play_preview, state='disabled')
        self.preview_btn.pack(side='left', padx=10)
        self.apply_btn = ttk.Button(bf, text="写入标签/封面", command=self.apply, state='disabled')
        self.apply_btn.pack(side='left', padx=10)

    def search(self):
        q = self.entry.get().strip()
        if not q: return self.root.after(0, lambda: self.status_var.set("️ 请输入"))
        self.results_data = [];
        self.selected_result = None;
        self.apply_btn.config(state='disabled');
        self.preview_btn.config(state='disabled')
        self.canvas.delete("all");
        self.cover_lbl.config(text="请选择结果", foreground="gray")
        for l in self.preview_labels.values(): l.config(text="-")
        [self.tree.delete(i) for i in self.tree.get_children()]
        self.root.after(0, lambda: self.status_var.set("🌐 搜索中..."))
        threading.Thread(target=self._search_worker, args=(q,), daemon=True).start()

    def _search_worker(self, q):
        try:
            r = session.get(API_BASE, params={'types': 'search', 'source': 'netease', 'name': q, 'count': '10'},
                            timeout=10)
            r.raise_for_status();
            data = r.json()
            if isinstance(data, list):
                for s in data:
                    if not isinstance(s, dict): continue
                    a = s.get('artist', []);
                    an = ', '.join(a) if isinstance(a, list) else str(a)
                    self.results_data.append(
                        {'id': s.get('id', ''), 'trackName': s.get('name', 'N/A'), 'artistName': an or 'N/A',
                         'collectionName': s.get('album', 'N/A'), 'trackNumber': '', 'artworkUrl': '',
                         'pic_id': s.get('pic_id', ''), 'source_name': s.get('source', 'netease'),
                         'previewUrl': '', 'releaseDate': '', 'source': 'GDStudio'})
            if not self.results_data:
                reg = {"country": REGIONS[self.region_var.get()], "lang": "zh-cn"}
                r2 = session.get(
                    f"https://itunes.apple.com/search?term={quote(q)}&media=music&limit=10&country={reg['country']}&lang={reg['lang']}",
                    timeout=10)
                r2.raise_for_status()
                for i in r2.json().get('results', []):
                    self.results_data.append({'id': i.get('trackId', ''), 'trackName': i.get('trackName', 'N/A'),
                                              'artistName': i.get('artistName', 'N/A'),
                                              'collectionName': i.get('collectionName', 'N/A'),
                                              'trackNumber': i.get('trackNumber', ''),
                                              'artworkUrl': i.get('artworkUrl100', ''),
                                              'previewUrl': i.get('previewUrl', ''),
                                              'releaseDate': i.get('releaseDate', ''), 'source': reg['country']})
            self.root.after(0, self._populate_tree)
        except Exception as e:
            self.root.after(0, lambda m=str(e): self.status_var.set(f"❌ {m}"))

    def _populate_tree(self):
        for i, r in enumerate(self.results_data):
            y = r.get('releaseDate', '')[:4] if r.get('releaseDate') else ''
            self.tree.insert("", "end", iid=i, values=(r['trackName'], r['artistName'], r['collectionName'], y))
        self.status_var.set(f"✅ {len(self.results_data)} 条结果")

    def on_select(self, e):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0]);
        self.selected_result = self.results_data[idx];
        r = self.selected_result
        for k, f in [(" 歌曲", 'trackName'), ("艺术家", 'artistName'), ("专辑", 'collectionName'),
                     ("轨号", 'trackNumber'), ("年份", 'releaseDate'), ("数据源", 'source')]:
            v = r.get(f, 'N/A')
            if f == 'releaseDate' and v != 'N/A': v = str(v)[:4]
            if f == 'trackNumber' and not v: v = 'N/A'
            self.preview_labels[k].config(text=v)
        self.cover_lbl.config(text="⬇加载封面...", foreground="blue")
        threading.Thread(target=self._load_cover, daemon=True).start()
        self.preview_btn.config(state='normal' if r.get('previewUrl') else 'disabled')
        self.status_var.set(f"{r['trackName']}");
        self.apply_btn.config(state='normal')

    def _load_cover(self):
        r = self.selected_result;
        url = ''
        if r.get('pic_id') and r.get('source_name'):
            try:
                d = session.get(API_BASE,
                                params={'types': 'pic', 'source': r['source_name'], 'id': r['pic_id'], 'size': '500'},
                                timeout=10).json()
                url = d.get('url', '') if isinstance(d, dict) else ''
            except:
                pass
        if not url and r.get('artworkUrl'):
            url = re.sub(r'/\d+x\d+bb\.(?:jpg|jpeg|png)$', '/1000x1000bb.jpg', r['artworkUrl']) if 'mzstatic.com' in r[
                'artworkUrl'] else r['artworkUrl']
        if not url: return self.root.after(0, lambda: self.cover_lbl.config(text=" 无封面", foreground="red"))
        try:
            resp = session.get(url, timeout=10);
            resp.raise_for_status()
            self.root.after(0, lambda d=resp.content: self._render_cover(d))
        except:
            self.root.after(0, lambda: self.cover_lbl.config(text="️ 失败", foreground="orange"))

    def _render_cover(self, data):
        try:
            img = Image.open(__import__('io').BytesIO(data)).resize((180, 180), Image.Resampling.LANCZOS)
            self.cover_tk = ImageTk.PhotoImage(img)
            self.canvas.create_image(90, 90, image=self.cover_tk)
            self.cover_lbl.config(text="已加载", foreground="green")
        except:
            self.cover_lbl.config(text="异常", foreground="red")

    def select_file(self):
        p = filedialog.askopenfilename(title="选择音频",
                                       filetypes=[("Audio", "*.mp3 *.m4a *.flac *.ogg *.wav"), ("All", "*.*")])
        if p: self.selected_file = p; self.file_lbl.config(text=f"📄 {os.path.basename(p)}"); self.status_var.set(
            " 已选")

    def play_preview(self):
        r = self.selected_result
        if not r.get('previewUrl'): return self.root.after(0, lambda: self.status_var.set("⚠️ 无预览"))

        def worker():
            try:
                resp = session.get(r['previewUrl'], timeout=10);
                resp.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as t:
                    t.write(resp.content); tp = t.name
                if os.name == 'nt':
                    os.startfile(tp)
                elif __import__('sys').platform == 'darwin':
                    subprocess.call(['open', tp])
                else:
                    subprocess.call(['xdg-open', tp])
                threading.Timer(60.0, lambda: os.remove(tp) if os.path.exists(tp) else None).start()
            except Exception as e:
                self.root.after(0, lambda m=str(e): self.status_var.set(f"{m}"))

        threading.Thread(target=worker, daemon=True).start()

    def apply(self):
        if not self.selected_file or not self.selected_result:
            return self.root.after(0, lambda: messagebox.showwarning("提示", "请先搜索并选择文件"))
        threading.Thread(target=self._apply_worker, daemon=True).start()

    def _apply_worker(self):
        self.root.after(0, lambda: self.status_var.set("处理中..."))
        try:
            r = self.selected_result;
            cover_data = None;
            mime = 'image/jpeg'
            url = r.get('artworkUrl', '')
            if r.get('pic_id') and r.get('source_name'):
                try:
                    d = session.get(API_BASE, params={'types': 'pic', 'source': r['source_name'], 'id': r['pic_id'],
                                                      'size': '500'}, timeout=10).json()
                    url = d.get('url', '') if isinstance(d, dict) else ''
                except:
                    pass
            if url:
                url = re.sub(r'/\d+x\d+bb\.(?:jpg|jpeg|png)$', '/1000x1000bb.jpg',
                             url) if 'mzstatic.com' in url else url
                resp = session.get(url, timeout=15);
                resp.raise_for_status()
                cover_data, mime = resp.content, resp.headers.get('Content-Type', 'image/jpeg')
            audio = mutagen.File(self.selected_file, easy=True)
            if audio is None: raise ValueError("不支持格式")
            audio['title'] = [r['trackName']];
            audio['artist'] = [r['artistName']];
            audio['album'] = [r['collectionName']]
            if r['trackNumber']: audio['tracknumber'] = [str(r['trackNumber'])]
            audio.save()
            if cover_data:
                audio = mutagen.File(self.selected_file)
                if isinstance(audio, mutagen.mp3.MP3):
                    if not audio.tags: audio.add_tags()
                    for k in list(audio.tags.keys()):
                        if k.startswith('APIC'): del audio.tags[k]
                    audio.tags.add(APIC(encoding=3, mime=mime, type=3, desc='Cover', data=cover_data));
                    audio.save(v2_version=3)
                elif isinstance(audio, mutagen.flac.FLAC):
                    p = Picture();
                    p.type = 3;
                    p.mime = mime;
                    p.data = cover_data;
                    audio.clear_pictures();
                    audio.add_picture(p);
                    audio.save()
                elif isinstance(audio, mutagen.mp4.MP4):
                    fmt = mutagen.mp4.AtomDataType.PNG if 'png' in mime else mutagen.mp4.AtomDataType.JPEG
                    audio['covr'] = [mutagen.mp4.MP4Cover(cover_data, imageformat=fmt)];
                    audio.save()
                elif type(audio).__name__ == 'WAVE':
                    self.root.after(0, lambda: self.status_var.set("️ WAV 无封面"))
            self.root.after(0, lambda: self.status_var.set("写入成功！"))
        except Exception as e:
            self.root.after(0, lambda m=str(e): self.status_var.set(f"{m}"))