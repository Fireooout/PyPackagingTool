import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import queue
import tokenize
import io
import platform

# 判断是否是打包后的环境
IS_FROZEN = getattr(sys, 'frozen', False)

class PackApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python打包工具 v3.0")
        self.root.geometry("950x750")
        
        # === GUI 美化 ===
        self._setup_styles()

        # === 变量初始化 ===
        self.python_interpreter = tk.StringVar()
        self.main_script_path = tk.StringVar()
        self.icon_path = tk.StringVar()
        self.output_name = tk.StringVar()
        self.output_dir = tk.StringVar()
        
        # 选项变量
        self.enable_upx = tk.BooleanVar(value=False)
        self.pack_option_var = tk.StringVar(value="single_dir") 
        self.console_window = tk.BooleanVar(value=False)
        
        # 图标策略: 1=默认, 2=自定义, 3=无
        self.icon_mode = tk.IntVar(value=1) 
        
        # 自动检测环境
        self._detect_python_interpreter()
        
        # === 默认图标逻辑 ===
        # 获取资源路径（兼容打包后和开发环境）
        self.base_path = sys._MEIPASS if IS_FROZEN else os.path.dirname(os.path.abspath(__file__))
        self.default_icon_path = os.path.join(self.base_path, "default.ico")
        
        # 列表与线程
        self.resource_files = []
        self.clean_files = []
        self.log_queue = queue.Queue()
        self.clean_log_queue = queue.Queue()
        
        # 启动检测
        if not IS_FROZEN:
            self._check_pyinstaller_installed()
            
        self.create_widgets()
        
        # 启动日志监听
        self.update_log()
        self.update_clean_log()

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except: pass
        
        BG_COLOR = "#F0F2F5"
        PRIMARY_COLOR = "#007AFF"
        TEXT_COLOR = "#333333"
        WHITE = "#FFFFFF"
        
        self.root.configure(bg=BG_COLOR)
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TLabelframe", background=BG_COLOR, foreground=TEXT_COLOR)
        style.configure("TLabelframe.Label", background=BG_COLOR, foreground="#555555", font=("微软雅黑", 10, "bold"))
        style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("微软雅黑", 9))
        style.configure("TButton", font=("微软雅黑", 9), padding=5)
        style.configure("TRadiobutton", background=BG_COLOR, font=("微软雅黑", 9))
        style.configure("TCheckbutton", background=BG_COLOR, font=("微软雅黑", 9))
        style.configure("Accent.TButton", foreground=WHITE, background=PRIMARY_COLOR, font=("微软雅黑", 10, "bold"))
        style.map("Accent.TButton", background=[('active', "#005BBB")])

    def _detect_python_interpreter(self):
        if IS_FROZEN:
            path = shutil.which("python")
            self.python_interpreter.set(path if path else "未检测到，请手动选择")
        else:
            self.python_interpreter.set(sys.executable)

    def _check_pyinstaller_installed(self):
        try:
            import PyInstaller
        except ImportError:
            if messagebox.askyesno("提示", "未检测到PyInstaller，是否安装？"):
                try:
                    subprocess.call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
                    messagebox.showinfo("成功", "安装完成")
                except Exception as e:
                    messagebox.showerror("错误", f"安装失败: {e}")

    def create_widgets(self):
        main_container = ttk.Frame(self.root, padding=10)
        main_container.pack(fill="both", expand=True)
        self.tab_control = ttk.Notebook(main_container)
        self.settings_tab = ttk.Frame(self.tab_control)
        self.log_tab = ttk.Frame(self.tab_control)
        self.clean_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.settings_tab, text=" ⚙️ 打包配置 ")
        self.tab_control.add(self.log_tab, text=" 📝 执行日志 ")
        self.tab_control.add(self.clean_tab, text=" 🧹 代码清洗 ")
        self.tab_control.pack(expand=True, fill="both")
        self._init_settings_tab()
        self._init_log_tab()
        self._init_clean_tab()

    def _init_settings_tab(self):
        # --- 环境区 ---
        env_frame = ttk.LabelFrame(self.settings_tab, text="核心环境")
        env_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(env_frame, text="Python解释器:").grid(row=0, column=0, padx=5)
        ttk.Entry(env_frame, textvariable=self.python_interpreter, width=70).grid(row=0, column=1, padx=5)
        ttk.Button(env_frame, text="选择...", command=self.select_interpreter).grid(row=0, column=2, padx=5, pady=5)
        
        # --- 项目区 ---
        proj_frame = ttk.LabelFrame(self.settings_tab, text="项目设置")
        proj_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(proj_frame, text="入口脚本(.py):").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(proj_frame, textvariable=self.main_script_path, width=70).grid(row=0, column=1, padx=5)
        ttk.Button(proj_frame, text="浏览...", command=self.select_main_script).grid(row=0, column=2, padx=5)
        ttk.Label(proj_frame, text="生成文件名:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(proj_frame, textvariable=self.output_name, width=30).grid(row=1, column=1, sticky="w", padx=5)

        # 图标设置区域
        icon_frame = ttk.LabelFrame(self.settings_tab, text="图标设置")
        icon_frame.pack(fill="x", padx=10, pady=5)
        has_default = os.path.exists(self.default_icon_path)
        default_txt = "使用内置默认图标" + (" (✅可用)" if has_default else " (❌未找到)")
        ttk.Radiobutton(icon_frame, text=default_txt, variable=self.icon_mode, value=1).grid(row=0, column=0, sticky="w", padx=10)
        ttk.Radiobutton(icon_frame, text="自定义图标:", variable=self.icon_mode, value=2).grid(row=1, column=0, sticky="w", padx=10)
        ttk.Radiobutton(icon_frame, text="不使用图标", variable=self.icon_mode, value=3).grid(row=2, column=0, sticky="w", padx=10)
        ttk.Entry(icon_frame, textvariable=self.icon_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(icon_frame, text="浏览", command=self.select_icon).grid(row=1, column=2, padx=5)
        
        # --- 资源区 ---
        res_frame = ttk.LabelFrame(self.settings_tab, text="资源文件 (图片/DLL/配置)")
        res_frame.pack(fill="both", expand=True, padx=10, pady=5)
        list_f = ttk.Frame(res_frame)
        list_f.pack(fill="both", expand=True, padx=5)
        self.res_list = tk.Listbox(list_f, height=4, relief="flat", bg="white", highlightthickness=1, highlightcolor="#ccc")
        self.res_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_f, command=self.res_list.yview)
        sb.pack(side="right", fill="y")
        self.res_list.config(yscrollcommand=sb.set)
        btn_f = ttk.Frame(res_frame)
        btn_f.pack(fill="x", pady=5)
        ttk.Button(btn_f, text="+ 添加文件", command=self.add_res_file).pack(side="left", padx=5)
        ttk.Button(btn_f, text="+ 添加文件夹", command=self.add_res_folder).pack(side="left", padx=5)
        ttk.Button(btn_f, text="- 删除选中", command=lambda: self._remove_sel(self.res_list, self.resource_files)).pack(side="left", padx=5)

        # --- 选项区 ---
        opt_frame = ttk.LabelFrame(self.settings_tab, text="打包参数")
        opt_frame.pack(fill="x", padx=10, pady=5)
        ttk.Radiobutton(opt_frame, text="单文件 (.exe)", variable=self.pack_option_var, value="single_file").pack(side="left", padx=10)
        ttk.Radiobutton(opt_frame, text="文件夹 (推荐排错)", variable=self.pack_option_var, value="single_dir").pack(side="left", padx=10)
        ttk.Radiobutton(opt_frame, text="依次生成两种 (Both)", variable=self.pack_option_var, value="both").pack(side="left", padx=10)
        ttk.Separator(opt_frame, orient="vertical").pack(side="left", fill="y", padx=10, pady=5)
        ttk.Checkbutton(opt_frame, text="显示控制台窗口 (Debug)", variable=self.console_window).pack(side="left", padx=5)
        ttk.Checkbutton(opt_frame, text="UPX压缩", variable=self.enable_upx).pack(side="left", padx=5)

        # --- 底部操作栏 ---
        act_frame = ttk.Frame(self.settings_tab)
        act_frame.pack(fill="x", padx=10, pady=15)
        ttk.Button(act_frame, text="🧹 清理临时文件", command=self.clean_temp).pack(side="left")
        ttk.Button(act_frame, text="🚀 开始打包", style="Accent.TButton", command=self.start_pack).pack(side="right", ipadx=20)

    def _init_log_tab(self):
        f = ttk.Frame(self.log_tab, padding=10)
        f.pack(fill="both", expand=True)
        self.log_text = tk.Text(f, wrap="word", bg="#1E1E1E", fg="#00FF00", font=("Consolas", 10))
        sb = ttk.Scrollbar(f, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.progress = ttk.Progressbar(self.log_tab, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=5)

    def _init_clean_tab(self):
        f = ttk.Frame(self.clean_tab, padding=10)
        f.pack(fill="both", expand=True)
        info_frame = ttk.Frame(f)
        info_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(info_frame, text="ℹ️ 功能说明：安全清洗将生成 '_clean.py' 新文件，仅删除 '#' 注释和空行。", foreground="#666").pack(anchor="w")
        paned = ttk.PanedWindow(f, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.LabelFrame(paned, text="待处理文件列表")
        paned.add(left, weight=1)
        self.clean_list = tk.Listbox(left, relief="flat", highlightthickness=1, highlightcolor="#ccc")
        self.clean_list.pack(fill="both", expand=True, padx=5, pady=5)
        l_btn = ttk.Frame(left)
        l_btn.pack(fill="x", padx=5, pady=5)
        ttk.Button(l_btn, text="+ 添加文件", command=self.add_clean_file).pack(side="left")
        ttk.Button(l_btn, text="清空列表", command=lambda: self._clear_list(self.clean_list, self.clean_files)).pack(side="right")
        right = ttk.LabelFrame(paned, text="处理日志")
        paned.add(right, weight=1)
        self.clean_log = tk.Text(right, height=10, bg="#FFF", font=("Consolas", 9))
        self.clean_log.pack(fill="both", expand=True, padx=5, pady=5)
        bot = ttk.Frame(f)
        bot.pack(fill="x", pady=10)
        self.clean_option_empty = tk.BooleanVar(value=True)
        ttk.Checkbutton(bot, text="删除多余空行", variable=self.clean_option_empty).pack(side="left", padx=10)
        ttk.Button(bot, text="🚀 开始清洗 (批量)", style="Accent.TButton", command=self.start_clean).pack(side="right", ipadx=10)

    # === 功能函数 ===
    def select_interpreter(self):
        p = filedialog.askopenfilename(filetypes=[("Python", "python.exe"), ("Exe", "*.exe")])
        if p: self.python_interpreter.set(p)

    def select_main_script(self):
        p = filedialog.askopenfilename(filetypes=[("Python", "*.py")])
        if p:
            self.main_script_path.set(p)
            if not self.output_name.get():
                self.output_name.set(os.path.splitext(os.path.basename(p))[0])

    def select_icon(self):
        p = filedialog.askopenfilename(filetypes=[("Icon", "*.ico")])
        if p: 
            self.icon_path.set(p)
            self.icon_mode.set(2)

    def add_res_file(self):
        fs = filedialog.askopenfilenames()
        for f in fs:
            if f not in self.resource_files:
                self.resource_files.append(f)
                self.res_list.insert(tk.END, f)
    
    def add_res_folder(self):
        d = filedialog.askdirectory()
        if d and d not in self.resource_files:
            self.resource_files.append(d)
            self.res_list.insert(tk.END, d)

    def _remove_sel(self, listbox, data_list):
        sel = listbox.curselection()
        for i in reversed(sel):
            listbox.delete(i)
            if i < len(data_list): data_list.pop(i)

    def _clear_list(self, listbox, data_list):
        listbox.delete(0, tk.END)
        data_list.clear()

    def add_clean_file(self):
        fs = filedialog.askopenfilenames(filetypes=[("Python", "*.py")])
        for f in fs:
            if f not in self.clean_files:
                self.clean_files.append(f)
                self.clean_list.insert(tk.END, f)

    def clean_temp(self, silent=False):
        if not self.main_script_path.get():
            if not silent: return
            return
        d = os.path.dirname(self.main_script_path.get())
        for x in ['build', 'dist', '__pycache__']:
            p = os.path.join(d, x)
            if os.path.exists(p): shutil.rmtree(p, ignore_errors=True)
        name = self.output_name.get()
        if name:
            spec = os.path.join(d, name + ".spec")
            if os.path.exists(spec): os.remove(spec)
        if not silent:
            messagebox.showinfo("完成", "临时文件已清理")
    
    def _open_output_folder(self, path):
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.log_queue.put(f"无法自动打开文件夹: {e}\n")

    # === 打包逻辑 ===
    def start_pack(self):
        if not self.main_script_path.get():
            return messagebox.showerror("错误", "未选择入口脚本")
        
        self.tab_control.select(self.log_tab)
        self.log_text.delete(1.0, tk.END)
        self.progress['value'] = 0
        threading.Thread(target=self._pack_thread, daemon=True).start()

    def _pack_thread(self):
        self.log_queue.put(">>> 正在自动清理旧构建文件...\n")
        self.clean_temp(silent=True)

        interpreter = self.python_interpreter.get()
        script = self.main_script_path.get()
        name = self.output_name.get()
        script_dir = os.path.dirname(os.path.abspath(script))
        
        mode = self.pack_option_var.get()
        modes_to_run = []
        if mode == 'single_file': modes_to_run = ['--onefile']
        elif mode == 'single_dir': modes_to_run = ['--onedir']
        elif mode == 'both': modes_to_run = ['--onedir', '--onefile']
        
        total = len(modes_to_run)
        
        for idx, current_mode in enumerate(modes_to_run):
            self.log_queue.put(f"\n>>> 正在启动第 {idx+1}/{total} 步: {current_mode} ...\n")
            
            # v3.4 核心变动：回归标准 collect-all，但依赖环境隔离
            cmd = [
                interpreter, "-m", "PyInstaller",
                script,
                "--noconfirm",
                "--clean",
                f"--name={name}",
                f"--distpath={os.path.join(script_dir, 'dist')}",
                f"--workpath={os.path.join(script_dir, 'build')}",
                f"--specpath={script_dir}",
                current_mode,
                "--collect-all=tkinter"  # 在纯净环境下，这是最安全的
            ]
            
            if not self.console_window.get(): cmd.append("--noconsole")
            if not self.enable_upx.get(): cmd.append("--noupx")
            
            # 图标逻辑
            imode = self.icon_mode.get()
            if imode == 2:
                ipath = self.icon_path.get()
                if ipath and os.path.exists(ipath):
                    cmd.append(f"--icon={ipath}")
                    self.log_queue.put(f"图标: 使用自定义 -> {ipath}\n")
            elif imode == 1:
                if os.path.exists(self.default_icon_path):
                    cmd.append(f"--icon={self.default_icon_path}")
                    self.log_queue.put(f"图标: 使用内置默认 -> {self.default_icon_path}\n")
            
            # 资源文件
            sep = ";" if os.name == 'nt' else ":"
            for r in self.resource_files:
                if os.path.exists(r):
                    dest = "." if os.path.isfile(r) else os.path.basename(r)
                    cmd.append(f"--add-data={r}{sep}{dest}")

            success = self._run_cmd(cmd)
            if not success:
                self.log_queue.put("\n❌ 失败终止。\n")
                return
        
        self.progress['value'] = 100
        dist_path = os.path.join(script_dir, 'dist')
        self.log_queue.put("\n✅ 任务完成！\n")
        messagebox.showinfo("成功", f"打包完成！\n路径: {dist_path}")
        self._open_output_folder(dist_path)

    def _run_cmd(self, cmd):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        except: startupinfo = None
            
        sys_encoding = 'gbk' if os.name == 'nt' else 'utf-8'
        
        # v3.4 核心修复：创建纯净的环境变量
        # 复制当前环境变量，但移除可能导致冲突的 TCL/TK 变量
        clean_env = os.environ.copy()
        keys_to_remove = ['TCL_LIBRARY', 'TK_LIBRARY', '_MEIPASS2'] # _MEIPASS2 是 PyInstaller 内部使用的
        for key in keys_to_remove:
            if key in clean_env:
                clean_env.pop(key)
        
        try:
            self.log_queue.put(f"Cmd: {' '.join(cmd)}\n")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=sys_encoding,
                errors='replace',
                startupinfo=startupinfo,
                env=clean_env # 传入净化后的环境
            )
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None: break
                if line:
                    self.log_queue.put(line)
                    if self.progress['value'] < 95: self.progress['value'] += 0.1
            return process.poll() == 0
        except Exception as e:
            self.log_queue.put(f"Error: {e}\n")
            return False

    # === 清洗逻辑 ===
    def start_clean(self):
        if not self.clean_files:
            return messagebox.showinfo("提示", "请先添加文件")
        self.clean_log.delete(1.0, tk.END)
        threading.Thread(target=self._clean_thread, daemon=True).start()

    def _clean_thread(self):
        total = len(self.clean_files)
        success = 0
        self.clean_log_queue.put(f"开始批量处理 {total} 个文件...\n")
        output_folder = None
        for idx, fpath in enumerate(self.clean_files):
            try:
                if output_folder is None:
                    output_folder = os.path.dirname(fpath)
                self.clean_log_queue.put(f"[{idx+1}/{total}] {os.path.basename(fpath)} ... ")
                new_path = self._clean_single_file(fpath)
                if new_path:
                    self.clean_log_queue.put("✅ 成功\n")
                    success += 1
            except Exception as e:
                self.clean_log_queue.put(f"❌ 失败: {str(e)}\n")
        self.clean_log_queue.put(f"\n完成！成功 {success}/{total}。\n")
        messagebox.showinfo("完成", "批量清洗完成！")
        if output_folder:
            self._open_output_folder(output_folder)

    def _clean_single_file(self, source_path):
        base, ext = os.path.splitext(source_path)
        new_path = f"{base}_clean{ext}"
        with open(source_path, 'rb') as f:
            tokens = list(tokenize.tokenize(f.readline))
            src_encoding = 'utf-8'
            if tokens and tokens[0].type == tokenize.ENCODING:
                src_encoding = tokens[0].string

        out_tokens = []
        for token in tokens:
            if token.type == tokenize.COMMENT:
                continue
            out_tokens.append(token)

        cleaned_bytes = tokenize.untokenize(out_tokens)
        cleaned_code = cleaned_bytes.decode(src_encoding)
        
        if self.clean_option_empty.get():
            lines = cleaned_code.splitlines()
            final_lines = []
            blank_count = 0
            for line in lines:
                if not line.strip():
                    blank_count += 1
                    if blank_count > 1: continue
                else:
                    blank_count = 0
                final_lines.append(line)
            cleaned_code = "\n".join(final_lines)

        with open(new_path, 'w', encoding=src_encoding) as f:
            f.write(cleaned_code)
        return new_path

    # === 日志刷新 ===
    def update_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg)
                self.log_text.see(tk.END)
        except queue.Empty: pass
        self.root.after(100, self.update_log)

    def update_clean_log(self):
        try:
            while True:
                msg = self.clean_log_queue.get_nowait()
                self.clean_log.insert(tk.END, msg)
                self.clean_log.see(tk.END)
        except queue.Empty: pass
        self.root.after(100, self.update_clean_log)

if __name__ == "__main__":
    root = tk.Tk()
    app = PackApp(root)
    root.mainloop()
