import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import subprocess
import os


class ConverterModule:
    def __init__(self, root, status_var):
        self.root = root
        self.status_var = status_var
        self.task_queue = queue.Queue()
        self.MAX_WORKERS = 2
        self.workers = []
        self.is_running = False
        self.tasks = []

    def create_ui(self, parent):
        cf = ttk.Frame(parent);
        cf.pack(pady=8, padx=10, fill='x')
        ttk.Label(cf, text="输出目录:").pack(side='left', padx=5)
        self.out_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Music/Converted"))
        ttk.Entry(cf, textvariable=self.out_var, width=40).pack(side='left', padx=5)
        ttk.Button(cf, text="浏览", command=self.select_out).pack(side='left')
        ttk.Button(cf, text="质量预设", state='disabled').pack(side='right')

        opt = ttk.Frame(parent);
        opt.pack(pady=5, padx=10, fill='x')
        ttk.Label(opt, text="转换质量:").pack(side='left', padx=(0, 10))
        self.quality = tk.StringVar(value="original")
        ttk.Radiobutton(opt, text="原声保留", variable=self.quality, value="original").pack(side='left', padx=5)
        ttk.Radiobutton(opt, text="定制压缩 (48kHz/512K)", variable=self.quality, value="compressed").pack(side='left',
                                                                                                           padx=5)

        lf = ttk.LabelFrame(parent, text="转换队列");
        lf.pack(pady=5, padx=10, fill='both', expand=True)
        self.listbox = tk.Listbox(lf, height=8, font=("Consolas", 9))
        self.listbox.pack(fill='both', expand=True, padx=5, pady=5)

        bf = ttk.Frame(parent);
        bf.pack(pady=8)
        ttk.Button(bf, text="添加文件", command=self.add_files).pack(side='left', padx=10)
        ttk.Button(bf, text="清空队列", command=self.clear_queue).pack(side='left', padx=10)
        self.start_btn = ttk.Button(bf, text="开始转换", command=self.start_conversion)
        self.start_btn.pack(side='left', padx=10)
        ttk.Label(parent, textvariable=self.status_var, relief='sunken', anchor='w').pack(fill='x', padx=10, pady=5)

    def select_out(self):
        p = filedialog.askdirectory(title="输出文件夹", initialdir=self.out_var.get())
        if p: self.out_var.set(p)

    def add_files(self):
        files = filedialog.askopenfilenames(title="选择音频文件",
                                            filetypes=[("Audio", "*.mp3 *.m4a *.flac *.ogg *.wav *.wma"),
                                                       ("All", "*.*")])
        for f in files:
            if f not in self.tasks:
                self.tasks.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))
        self.status_var.set(f"已添加 {len(self.tasks)} 个文件")

    def clear_queue(self):
        if self.is_running: return messagebox.showwarning("提示", "转换进行中，无法清空")
        self.tasks.clear();
        self.listbox.delete(0, tk.END)
        self.status_var.set("队列已清空")

    def start_conversion(self):
        if not self.tasks: return messagebox.showwarning("提示", "请先添加文件")
        if self.is_running: return
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except FileNotFoundError:
            return messagebox.showerror("缺少依赖", "未检测到 FFmpeg！请安装并添加至 PATH。")

        self.is_running = True;
        self.start_btn.config(state='disabled')
        for t in self.tasks: self.task_queue.put(t)
        for _ in range(self.MAX_WORKERS):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start();
            self.workers.append(t)
        self.status_var.set("转换任务已派发...")

    def _worker(self):
        while True:
            try:
                inp = self.task_queue.get(timeout=1)
            except queue.Empty:
                break
            try:
                self._process_file(inp)
            except Exception as e:
                self.root.after(0, lambda m=str(e), f=os.path.basename(inp): self.status_var.set(f"{f} 转换失败: {m}"))
            finally:
                self.task_queue.task_done()

        if all(not t.is_alive() for t in self.workers) and self.task_queue.empty():
            self.root.after(0, self._on_finish)

    def _process_file(self, inp):
        self.root.after(0, lambda f=os.path.basename(inp): self.status_var.set(f"正在转换: {f}"))
        od = self.out_var.get();
        os.makedirs(od, exist_ok=True)
        bn = os.path.splitext(os.path.basename(inp))[0]
        op = os.path.join(od, f"{bn}.m4a")
        c = 1
        while os.path.exists(op): op = os.path.join(od, f"{bn}_{c}.m4a"); c += 1

        cmd = ['ffmpeg', '-y', '-i', inp, '-c:a', 'alac']
        if self.quality.get() == 'compressed': cmd.extend(['-ar', '48000', '-b:a', '512k'])
        cmd.append(op)

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                                errors='ignore')
        _, err = proc.communicate()
        if proc.returncode != 0: raise RuntimeError(f"FFmpeg: {err[:100]}")
        self.root.after(0, lambda f=os.path.basename(op): self.status_var.set(f"转换完成: {f}"))

    def _on_finish(self):
        self.is_running = False;
        self.workers.clear()
        self.start_btn.config(state='normal')
        self.status_var.set("所有转换任务已完成！")
        if messagebox.askyesno("完成", "打开输出文件夹？"): os.startfile(self.out_var.get())