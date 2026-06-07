import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import mutagen
from mutagen.id3 import USLT
import mutagen.mp4
import threading, os, time
from config import session, API_BASE

class LyricsModule:
    def __init__(self, root, status_var):
        self.root = root
        self.status_var = status_var
        self.audio_path = None

    def create_ui(self, parent):
        af = ttk.LabelFrame(parent, text="目标音频文件"); af.pack(pady=5, padx=10, fill='x')
        ttk.Label(af, text="路径:").pack(side='left', padx=5)
        self.file_var = tk.StringVar(value="未选择")
        ttk.Entry(af, textvariable=self.file_var, width=50, state='readonly').pack(side='left', padx=5)
        ttk.Button(af, text="选择音频", command=self.select_audio).pack(side='left')

        ls = ttk.LabelFrame(parent, text="歌词来源"); ls.pack(pady=5, padx=10, fill='x')
        self.source_var = tk.StringVar(value="file")
        ttk.Radiobutton(ls, text="本地文件 (.lrc/.txt)", variable=self.source_var, value="file", command=self.toggle_ui).pack(side='left', padx=10)
        ttk.Radiobutton(ls, text="手动输入 / API获取", variable=self.source_var, value="input", command=self.toggle_ui).pack(side='left', padx=10)

        lc = ttk.Frame(parent); lc.pack(pady=5, padx=10, fill='both', expand=True)
        self.file_mode = ttk.Frame(lc)
        self.path_entry = ttk.Entry(self.file_mode, width=60); self.path_entry.pack(pady=5)
        ttk.Button(self.file_mode, text="选择歌词文件", command=self.select_lyric).pack(pady=5)

        self.input_mode = ttk.Frame(lc)
        sf = ttk.Frame(self.input_mode); sf.pack(fill='x', pady=2)
        ttk.Label(sf, text="歌名:").pack(side='left')
        self.name_entry = ttk.Entry(sf, width=20); self.name_entry.pack(side='left', padx=2)
        ttk.Label(sf, text="歌手:").pack(side='left')
        self.artist_entry = ttk.Entry(sf, width=15); self.artist_entry.pack(side='left', padx=2)
        ttk.Button(sf, text="自动获取", command=self.fetch_lyrics).pack(side='left', padx=5)
        self.text_box = tk.Text(self.input_mode, height=8, font=("Consolas", 9))
        self.text_box.pack(fill='both', expand=True, pady=2)

        bf = ttk.Frame(parent); bf.pack(pady=10)
        ttk.Button(bf, text="嵌入歌词", command=self.embed).pack(side='left', padx=20)
        self.toggle_ui()

    def toggle_ui(self):
        if self.source_var.get() == 'file':
            self.file_mode.pack(fill='x', pady=5); self.input_mode.pack_forget()
        else:
            self.file_mode.pack_forget(); self.input_mode.pack(fill='both', expand=True)

    def select_audio(self):
        p = filedialog.askopenfilename(title="选择目标音频", filetypes=[("Audio","*.mp3 *.m4a *.flac *.ogg *.wav"),("All","*.*")])
        if p: self.audio_path = p; self.file_var.set(os.path.basename(p)); self.status_var.set("音频已选择")

    def select_lyric(self):
        p = filedialog.askopenfilename(title="选择歌词文件", filetypes=[("Lyrics","*.lrc *.txt"),("All","*.*")])
        if p:
            self.path_entry.delete(0, tk.END); self.path_entry.insert(0, p)
            try:
                enc = 'utf-8'
                try: open(p, 'r', encoding='utf-8').read()
                except: enc = 'gbk'
                with open(p, 'r', encoding=enc) as f: txt = f.read()
                self.text_box.delete(1.0, tk.END); self.text_box.insert(1.0, txt)
                self.source_var.set("input"); self.toggle_ui()
                self.status_var.set("歌词已加载")
            except Exception as e: self.status_var.set(f"读取失败: {e}")

    def fetch_lyrics(self):
        threading.Thread(target=self._fetch_worker, daemon=True).start()
    def _fetch_worker(self):
        n = self.name_entry.get().strip(); a = self.artist_entry.get().strip()
        if not n: return self.root.after(0, lambda: self.status_var.set("请输入歌名"))
        q = f"{n} {a}" if a else n
        for attempt in range(1, 4):
            self.root.after(0, lambda a=attempt: self.status_var.set(f"正在尝试获取歌词 ({a}/3)..."))
            try:
                r1 = session.get(API_BASE, params={'types':'search','source':'netease','name':q,'count':'1'}, timeout=8)
                r1.raise_for_status(); d1 = r1.json()
                if isinstance(d1, list) and d1:
                    lid = d1[0].get('lyric_id') or d1[0].get('id')
                    if lid:
                        rl1 = session.get(API_BASE, params={'types':'lyric','source':'netease','id':lid}, timeout=8)
                        rl1.raise_for_status(); ld1 = rl1.json()
                        if isinstance(ld1, dict) and ld1.get('lyric'):
                            self.root.after(0, lambda l=ld1['lyric']: self.text_box.delete(1.0, tk.END) or self.text_box.insert(1.0, l))
                            return self.root.after(0, lambda: self.status_var.set("歌词获取成功"))
                self.root.after(0, lambda: self.status_var.set(f"切换至酷我重试 ({attempt}/3)..."))
                r2 = session.get(API_BASE, params={'types':'search','source':'kuwo','name':q,'count':'1'}, timeout=8)
                r2.raise_for_status(); d2 = r2.json()
                if isinstance(d2, list) and d2:
                    lid2 = d2[0].get('lyric_id') or d2[0].get('id')
                    if lid2:
                        rl2 = session.get(API_BASE, params={'types':'lyric','source':'kuwo','id':lid2}, timeout=8)
                        rl2.raise_for_status(); ld2 = rl2.json()
                        if isinstance(ld2, dict) and ld2.get('lyric'):
                            self.root.after(0, lambda l=ld2['lyric']: self.text_box.delete(1.0, tk.END) or self.text_box.insert(1.0, l))
                            return self.root.after(0, lambda: self.status_var.set("歌词获取成功"))
                if attempt < 3: time.sleep(1.5)
            except: pass
        self.root.after(0, lambda: self.status_var.set("获取失败，请手动输入"))

    def embed(self):
        if not self.audio_path: return messagebox.showwarning("提示","请先选择目标音频")
        threading.Thread(target=self._embed_worker, daemon=True).start()
    def _embed_worker(self):
        self.root.after(0, lambda: self.status_var.set("正在读取歌词..."))
        try:
            lyrics = self.text_box.get(1.0, tk.END).strip() if self.source_var.get()=="input" else open(self.path_entry.get(),'r',encoding='utf-8' if open(self.path_entry.get(),'rb').read(3)!=b'\xef\xbb\xbf' else 'gbk').read()
            if not lyrics: raise ValueError("歌词内容为空")
            self.root.after(0, lambda: self.status_var.set("正在写入..."))
            audio = mutagen.File(self.audio_path)
            if audio is None: raise ValueError("不支持的音频格式")
            if isinstance(audio, mutagen.mp3.MP3):
                try:
                    tags = mutagen.id3.ID3(self.audio_path) if audio.tags else mutagen.id3.ID3()
                    for k in list(tags.keys()):
                        if k.startswith('USLT'): del tags[k]
                    tags.add(USLT(encoding=3, lang='zho', desc='', text=lyrics))
                    tags.save(v2_version=3)
                except Exception as mp3_err:
                    if 'sync' in str(mp3_err).lower(): raise RuntimeError("MP3 音频帧损坏，建议用 FFmpeg 修复后再试。")
                    raise mp3_err
            elif isinstance(audio, mutagen.flac.FLAC): audio['LYRICS'] = lyrics; audio.save()
            elif isinstance(audio, mutagen.mp4.MP4): audio['\xa9lyr'] = lyrics; audio.save()
            else: raise TypeError("仅支持 MP3 / FLAC / M4A")
            self.root.after(0, lambda: self.status_var.set("歌词嵌入成功"))
        except Exception as e: self.root.after(0, lambda m=str(e): self.status_var.set(f"失败: {m}"))