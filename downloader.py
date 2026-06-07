import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re, threading, os, time
from config import session, API_BASE, STABLE_SOURCES, QUALITY_MAP

class DownloaderModule:
    def __init__(self, root, status_var, tagger_apply_func):
        self.root = root
        self.status_var = status_var
        self.tagger_apply = tagger_apply_func
        self.results_data = []
        self.selected_download = None

    def create_ui(self, parent):
        cf = ttk.Frame(parent); cf.pack(pady=8, padx=10, fill='x')
        ttk.Label(cf, text="搜索:").grid(row=0, column=0, padx=(0,5), sticky='w')
        self.entry = ttk.Entry(cf, width=30); self.entry.grid(row=0, column=1, padx=5)
        self.entry.bind("<Return>", lambda e: self.search())
        ttk.Label(cf, text="来源:").grid(row=0, column=2, padx=(10,5), sticky='w')
        self.source_var = tk.StringVar(value="网易云音乐 (netease)")
        sc = ttk.Combobox(cf, textvariable=self.source_var, state="readonly", width=22, values=list(STABLE_SOURCES.keys()))
        sc.grid(row=0, column=3, padx=5); sc.current(0)
        ttk.Label(cf, text="音质:").grid(row=0, column=4, padx=(10,5), sticky='w')
        self.quality_var = tk.StringVar(value="无损音质 (FLAC)")
        qc = ttk.Combobox(cf, textvariable=self.quality_var, state="readonly", width=20, values=list(QUALITY_MAP.keys()))
        qc.grid(row=0, column=5, padx=5); qc.current(2)
        ttk.Button(cf, text="搜索", command=self.search).grid(row=0, column=6, padx=5)

        tf = ttk.Frame(parent); tf.pack(pady=5, padx=10, fill='both', expand=True)
        cols = ("song","artist","album","source")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", height=12)
        for c,t in zip(cols,["歌曲","艺术家","专辑","来源"]): self.tree.heading(c, text=t)
        self.tree.column("song", width=200); self.tree.column("artist", width=120)
        self.tree.column("album", width=150); self.tree.column("source", width=80, anchor='center')
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill='both', expand=True); self.tree.bind("<<TreeviewSelect>>", self.on_select)

        df = ttk.Frame(parent); df.pack(pady=5, padx=10, fill='x')
        ttk.Label(df, text="保存路径:").pack(side='left')
        self.path_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Music"))
        ttk.Entry(df, textvariable=self.path_var, width=45).pack(side='left', padx=5)
        ttk.Button(df, text="浏览", command=self.select_path).pack(side='left')
        bf = ttk.Frame(parent); bf.pack(pady=8)
        ttk.Button(bf, text="试听", command=lambda: messagebox.showinfo("提示","试听请使用标签页1"), state='disabled').pack(side='left', padx=10)
        self.dl_btn = ttk.Button(bf, text="下载选中", command=self.download, state='disabled')
        self.dl_btn.pack(side='left', padx=10)

    def select_path(self):
        p = filedialog.askdirectory(title="保存文件夹", initialdir=self.path_var.get())
        if p: self.path_var.set(p); self.status_var.set(f"已设置: {p}")

    def search(self):
        q = self.entry.get().strip()
        if not q: return self.root.after(0, lambda: self.status_var.set("请输入查询词"))
        self.results_data=[]; self.selected_download=None; self.dl_btn.config(state='disabled')
        [self.tree.delete(i) for i in self.tree.get_children()]
        sc = STABLE_SOURCES[self.source_var.get()]
        self.root.after(0, lambda: self.status_var.set(f"正在搜索: {self.source_var.get()}..."))
        threading.Thread(target=self._search_worker, args=(q, sc), daemon=True).start()

    def _search_worker(self, q, sc):
        try:
            time.sleep(0.2)
            r = session.get(API_BASE, params={'types':'search','source':sc,'name':q,'count':'15'}, timeout=10)
            r.raise_for_status(); data = r.json()
            if not isinstance(data, list): return self.root.after(0, lambda: self.status_var.set("返回格式异常"))
            for s in data:
                if not isinstance(s, dict): continue
                a = s.get('artist',[]); an = ', '.join(a) if isinstance(a,list) else str(a)
                self.results_data.append({'id':s.get('id',''),'name':s.get('name','N/A'),'artist':an,'album':s.get('album','N/A'),'pic_id':s.get('pic_id',''),'source':sc})
            self.root.after(0, self._populate_tree)
        except Exception as e: self.root.after(0, lambda m=str(e): self.status_var.set(f"搜索失败: {m}"))

    def _populate_tree(self):
        for i,s in enumerate(self.results_data): self.tree.insert("","end",iid=i,values=(s['name'],s['artist'],s['album'],s['source']))
        self.status_var.set(f"找到 {len(self.results_data)} 首歌曲")

    def on_select(self, e):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0]); self.selected_download = self.results_data[idx]
        self.status_var.set(f"已选择: {self.selected_download['name']}"); self.dl_btn.config(state='normal')

    def download(self):
        if not self.selected_download: return self.root.after(0, lambda: messagebox.showwarning("提示","请先选择歌曲"))
        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        s = self.selected_download; br = QUALITY_MAP[self.quality_var.get()]; sd = self.path_var.get(); os.makedirs(sd, exist_ok=True)
        self.root.after(0, lambda: self.status_var.set("正在请求下载链接..."))
        try:
            time.sleep(0.2)
            r = session.get(API_BASE, params={'types':'url','source':s['source'],'id':s['id'],'br':br}, timeout=15)
            r.raise_for_status(); data = r.json()
            if not isinstance(data, dict) or not data.get('url'): raise ValueError(f"获取链接失败: {data.get('msg','未知错误')}")
            url = data['url']; ab = data.get('br',br)
            ext = '.flac' if str(ab) in ['740','999','740000','999000'] else '.mp3'
            sn = re.sub(r'[<>:"/\\|?*]','',f"{s['name']} - {s['artist']}"); sp = os.path.join(sd, f"{sn}{ext}")
            c=1
            while os.path.exists(sp): sp=os.path.join(sd, f"{sn} ({c}){ext}"); c+=1
            self.root.after(0, lambda: self.status_var.set("正在下载..."))
            dr = session.get(url, stream=True, timeout=30); dr.raise_for_status()
            tot = int(dr.headers.get('content-length',0)); dl=0
            with open(sp,'wb') as f:
                for ch in dr.iter_content(chunk_size=8192):
                    if ch: f.write(ch); dl+=len(ch)
                    if tot>0: self.root.after(0, lambda p=(dl/tot)*100: self.status_var.set(f"下载进度: {p:.1f}%"))
            self.root.after(0, lambda: self.status_var.set(f"下载完成: {os.path.basename(sp)}"))
            if messagebox.askyesno("完成","是否立即写入标签与封面？"):
                self.tagger_apply(sp, s)
        except Exception as e: self.root.after(0, lambda m=str(e): self.status_var.set(f"下载失败: {m}"))