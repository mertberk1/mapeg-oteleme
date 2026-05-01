"""
MAPEG İmalat Haritası - Otomatik Öteleme Programı v2.0
"""

import re
import math
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# ======================== AYARLAR ========================
DEFAULT_OFFSET = 0.20
DEFAULT_DIRECTION = 'left'
DEFAULT_TEXT_HEIGHT = 0.3
DEFAULT_LAYER = 'OTELEME'
# =========================================================


def parse_koordinat_txt(filepath):
    for enc in ['cp1254', 'utf-8', 'latin-1']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                text = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        raise ValueError(f"Dosya okunamadi: {filepath}")
    rows = []
    for line in text.split('\n'):
        clean = re.sub(r'[^\d\.\s\-,]', ' ', line).strip()
        parts = clean.replace(',', ' ').split()
        if len(parts) >= 4:
            try:
                rows.append({'no': int(float(parts[0])), 'x': float(parts[1]),
                             'y': float(parts[2]), 'z': float(parts[3])})
            except (ValueError, IndexError):
                continue
    return rows


def parse_dxf(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read()
    text = raw.decode('cp1254', errors='replace')
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    all_points = []; telk_lines = []; sevalt_verts = set(); max_handle = 0
    i = 0; in_ent = False
    while i < len(lines) - 1:
        c = lines[i].strip(); v = lines[i + 1].strip()
        if c == '2' and v == 'ENTITIES': in_ent = True; i += 2; continue
        if c == '0' and v == 'ENDSEC' and in_ent: break
        if c == '5':
            try: max_handle = max(max_handle, int(v, 16))
            except: pass
        if in_ent and c == '0' and v == 'POINT':
            layer = '0'; x = y = z = 0.0
            i += 2
            while i < len(lines) - 1:
                c2 = lines[i].strip(); v2 = lines[i + 1].strip()
                if c2 == '0': break
                if c2 == '8': layer = v2
                if c2 == '10': x = float(v2)
                if c2 == '20': y = float(v2)
                if c2 == '30': z = float(v2)
                i += 2
            all_points.append({'layer': layer, 'x': x, 'y': y, 'z': z})
            continue
        if in_ent and c == '0' and v == 'LINE':
            layer = '0'; x1 = y1 = z1 = x2 = y2 = z2 = 0.0
            i += 2
            while i < len(lines) - 1:
                c2 = lines[i].strip(); v2 = lines[i + 1].strip()
                if c2 == '0': break
                if c2 == '8': layer = v2
                if c2 == '10': x1 = float(v2)
                if c2 == '20': y1 = float(v2)
                if c2 == '30': z1 = float(v2)
                if c2 == '11': x2 = float(v2)
                if c2 == '21': y2 = float(v2)
                if c2 == '31': z2 = float(v2)
                i += 2
            if layer == 'TELKESME': telk_lines.append(((x1, y1, z1), (x2, y2, z2)))
            elif layer == 'SEVALT': sevalt_verts.add((round(x1, 3), round(y1, 3))); sevalt_verts.add((round(x2, 3), round(y2, 3)))
            continue
        i += 1
    return raw, all_points, telk_lines, sevalt_verts, max_handle


def build_chains(ll, tol=0.001):
    used = [False] * len(ll); chains = []
    for idx in range(len(ll)):
        if used[idx]: continue
        p1, p2 = ll[idx]; chain = [p1, p2]; used[idx] = True
        changed = True
        while changed:
            changed = False
            for j in range(len(ll)):
                if used[j]: continue
                a, b = ll[j]; end = chain[-1]; start = chain[0]
                if abs(a[0]-end[0])<tol and abs(a[1]-end[1])<tol: chain.append(b); used[j]=True; changed=True
                elif abs(b[0]-end[0])<tol and abs(b[1]-end[1])<tol: chain.append(a); used[j]=True; changed=True
                elif abs(b[0]-start[0])<tol and abs(b[1]-start[1])<tol: chain.insert(0,a); used[j]=True; changed=True
                elif abs(a[0]-start[0])<tol and abs(a[1]-start[1])<tol: chain.insert(0,b); used[j]=True; changed=True
        chains.append(chain)
    return chains


def build_spatial_index(chains, cell=5.0):
    sp = {}
    for ci, ch in enumerate(chains):
        for vi, v in enumerate(ch):
            cx = int(v[0]/cell); cy = int(v[1]/cell)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    k = (cx+dx, cy+dy)
                    if k not in sp: sp[k] = []
                    sp[k].append((ci, vi))
    return sp


def get_offset(prev, curr, nxt, dist, direction='left'):
    if prev and nxt:
        n1x=-(curr[1]-prev[1]); n1y=curr[0]-prev[0]; l1=math.sqrt(n1x**2+n1y**2) or 1
        n2x=-(nxt[1]-curr[1]); n2y=nxt[0]-curr[0]; l2=math.sqrt(n2x**2+n2y**2) or 1
        dx=(n1x/l1+n2x/l2)/2; dy=(n1y/l1+n2y/l2)/2
    elif nxt: dx=-(nxt[1]-curr[1]); dy=nxt[0]-curr[0]
    elif prev: dx=-(curr[1]-prev[1]); dy=curr[0]-prev[0]
    else: return (curr[0], curr[1]+dist)
    l = math.sqrt(dx**2+dy**2) or 1; dx /= l; dy /= l
    if direction == 'right': dx = -dx; dy = -dy
    return (curr[0]+dx*dist, curr[1]+dy*dist)


def nearest_sevust_pt(px, py, su_list, su_sp):
    """En yakın SEVUST noktasını bulur."""
    cx = int(px/10); cy = int(py/10)
    best_d = float('inf'); best_pt = None
    for idx in su_sp.get((cx, cy), []):
        sx, sy = su_list[idx]
        d = math.sqrt((sx-px)**2 + (sy-py)**2)
        if d < best_d: best_d = d; best_pt = (sx, sy)
    if best_pt is None:
        for sx, sy in su_list:
            d = math.sqrt((sx-px)**2 + (sy-py)**2)
            if d < best_d: best_d = d; best_pt = (sx, sy)
    return best_pt


def get_offset_smart(prev, curr, nxt, dist, sevust_pt):
    """Ötelemeyi şev üstünden UZAĞA doğru yapar."""
    if prev and nxt:
        n1x=-(curr[1]-prev[1]); n1y=curr[0]-prev[0]; l1=math.sqrt(n1x**2+n1y**2) or 1
        n2x=-(nxt[1]-curr[1]); n2y=nxt[0]-curr[0]; l2=math.sqrt(n2x**2+n2y**2) or 1
        dx=(n1x/l1+n2x/l2)/2; dy=(n1y/l1+n2y/l2)/2
    elif nxt: dx=-(nxt[1]-curr[1]); dy=nxt[0]-curr[0]
    elif prev: dx=-(curr[1]-prev[1]); dy=curr[0]-prev[0]
    else: return (curr[0], curr[1]+dist)
    l = math.sqrt(dx**2+dy**2) or 1; dx /= l; dy /= l
    left_x = curr[0]+dx*dist; left_y = curr[1]+dy*dist
    right_x = curr[0]-dx*dist; right_y = curr[1]-dy*dist
    d_left = math.sqrt((left_x-sevust_pt[0])**2+(left_y-sevust_pt[1])**2)
    d_right = math.sqrt((right_x-sevust_pt[0])**2+(right_y-sevust_pt[1])**2)
    return (left_x, left_y) if d_left >= d_right else (right_x, right_y)


def process(dxf_path, txt_path, output_dir, offset_dist, direction, log_func):
    log = log_func

    log("=" * 50)
    log("  MAPEG Öteleme İşlemi Başladı")
    log("=" * 50)
    log("")

    base = os.path.splitext(os.path.basename(dxf_path))[0]

    log("[1/6] Dosyalar okunuyor...")
    telk_txt = parse_koordinat_txt(txt_path)
    log(f"  TXT: {len(telk_txt)} TELKESME noktası ({telk_txt[0]['no']}-{telk_txt[-1]['no']})")

    raw, all_points, telk_lines, sevalt_verts, max_handle = parse_dxf(dxf_path)
    log(f"  DXF: {len(all_points)} POINT, {len(telk_lines)} TELKESME LINE")

    log("[2/6] Koordinat bazlı numaralama...")
    txt_name_lookup = {}
    for pt in telk_txt:
        key = (round(pt['x'], 3), round(pt['y'], 3))
        txt_name_lookup[key] = pt['no']
    seq = 1
    for pt in all_points:
        key = (round(pt['x'], 3), round(pt['y'], 3))
        if pt['layer'] == 'TELKESME' and key in txt_name_lookup:
            pt['no'] = txt_name_lookup[key]
        else:
            pt['no'] = seq
        seq += 1
    log(f"  {len(all_points)} nokta numaralandı (koordinat eşleştirme)")

    # SEVUST spatial index for direction
    su_list = list(sevalt_verts)  # will rebuild below
    # Re-parse to get SEVUST separately
    text_dec = raw.decode('cp1254', errors='replace')
    lines_dec = text_dec.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    sevust_verts_list = []
    sevust_set = set()
    ii = 0; in_e = False
    while ii < len(lines_dec) - 1:
        cc = lines_dec[ii].strip(); vv = lines_dec[ii+1].strip()
        if cc == '2' and vv == 'ENTITIES': in_e = True; ii += 2; continue
        if cc == '0' and vv == 'ENDSEC' and in_e: break
        if in_e and cc == '0' and vv == 'LINE':
            lyr = '0'; x1=y1=x2=y2=0
            ii += 2
            while ii < len(lines_dec) - 1:
                c2 = lines_dec[ii].strip(); v2 = lines_dec[ii+1].strip()
                if c2 == '0': break
                if c2 == '8': lyr = v2
                if c2 == '10': x1 = float(v2)
                if c2 == '20': y1 = float(v2)
                if c2 == '11': x2 = float(v2)
                if c2 == '21': y2 = float(v2)
                ii += 2
            if lyr == 'SEVUST':
                for vx, vy in [(x1,y1),(x2,y2)]:
                    k = (round(vx,3),round(vy,3))
                    if k not in sevust_set:
                        sevust_set.add(k)
                        sevust_verts_list.append(k)
            continue
        ii += 1
    log(f"  SEVUST: {len(sevust_verts_list)} vertex (yön hesabı için)")

    su_sp = {}
    for i, (sx, sy) in enumerate(sevust_verts_list):
        cx = int(sx/10); cy = int(sy/10)
        for ddx in (-1,0,1):
            for ddy in (-1,0,1):
                k = (cx+ddx, cy+ddy)
                if k not in su_sp: su_sp[k] = []
                su_sp[k].append(i)

    log("[3/6] Zincirler oluşturuluyor...")
    chains = build_chains(telk_lines)
    sp = build_spatial_index(chains)
    log(f"  {len(chains)} zincir")

    log("[4/6] Öteleme hesaplanıyor (şev üstünden uzağa)...")
    offset_points = []
    for pt in telk_txt:
        px, py, pz = pt['x'], pt['y'], pt['z']
        if (round(px, 3), round(py, 3)) not in sevalt_verts:
            continue
        cx = int(px/5); cy = int(py/5)
        best_d = float('inf'); bc = bv = None
        for ci, vi in sp.get((cx, cy), []):
            v = chains[ci][vi]; d = math.sqrt((v[0]-px)**2+(v[1]-py)**2)
            if d < best_d: best_d = d; bc = ci; bv = vi
        if bc is None or best_d > 0.5: continue
        ch = chains[bc]
        prev = ch[bv-1] if bv > 0 else None
        curr = ch[bv]
        nxt = ch[bv+1] if bv < len(ch)-1 else None
        su_pt = nearest_sevust_pt(px, py, sevust_verts_list, su_sp)
        ox, oy = get_offset_smart(prev, curr, nxt, offset_dist, su_pt)
        offset_points.append({'no': pt['no'], 'x': ox, 'y': oy, 'z': pz})

    log(f"  {len(offset_points)} şev altı noktası ötelendi")

    log("[5/6] NCN dosyası yazılıyor...")
    ncn_path = os.path.join(output_dir, f"{base}_TUMU.ncn")
    with open(ncn_path, 'w', encoding='cp1254') as f:
        for pt in all_points:
            f.write(f"{pt['no']} {pt['x']:.6f} {pt['y']:.6f} {pt['z']:.6f}\n")
        for pt in offset_points:
            f.write(f"{pt['no']} {pt['x']:.6f} {pt['y']:.6f} {pt['z']:.6f}\n")
    total = len(all_points) + len(offset_points)
    log(f"  {ncn_path}")
    log(f"  {total} nokta ({len(all_points)} orijinal + {len(offset_points)} ötelenmiş)")

    log("[6/6] DXF yazılıyor...")
    next_handle = max_handle + 100
    new_bytes = b''
    for pt in offset_points:
        h = f'{next_handle:X}'; next_handle += 1
        s = (f'  0\r\nPOINT\r\n  5\r\n{h}\r\n330\r\n1F\r\n'
             f'100\r\nAcDbEntity\r\n  8\r\nOTELEME\r\n'
             f'100\r\nAcDbPoint\r\n'
             f' 10\r\n{pt["x"]}\r\n 20\r\n{pt["y"]}\r\n 30\r\n{pt["z"]}\r\n')
        new_bytes += s.encode('cp1254')
    ent = raw.find(b'ENTITIES\r\n')
    end = raw.find(b'  0\r\nENDSEC', ent + 10)
    result = raw[:end] + new_bytes + raw[end:]
    dxf_path_out = os.path.join(output_dir, f"{base}_otelenmis.dxf")
    with open(dxf_path_out, 'wb') as f:
        f.write(result)
    log(f"  {dxf_path_out}")

    log("")
    log("=" * 50)
    log(f"  TAMAMLANDI!")
    log(f"  Toplam nokta: {len(all_points)}")
    log(f"  Ötelenen: {len(offset_points)}")
    log(f"  Mesafe: {offset_dist}m {direction}")
    log("=" * 50)
    log("")
    log("NetCAD'de:")
    log("1. Orijinal NCZ'yi açın")
    log("2. Nokta Editörü → Yükle → _TUMU.ncn")
    log("3. Çizime Sakla")

    return ncn_path, dxf_path_out


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("MAPEG Öteleme Aracı v2.0")
        self.root.geometry("700x620")
        self.root.resizable(True, True)

        try:
            self.root.iconbitmap(default='')
        except:
            pass

        style = ttk.Style()
        style.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'))
        style.configure('Sub.TLabel', font=('Segoe UI', 9), foreground='#666')
        style.configure('Big.TButton', font=('Segoe UI', 11, 'bold'), padding=10)

        main = ttk.Frame(root, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(main, text="⛏ MAPEG Öteleme Aracı", style='Title.TLabel').pack(anchor=tk.W)
        ttk.Label(main, text="İmalat Haritası - Şev Altı Otomatik Öteleme ve Numaralama", style='Sub.TLabel').pack(anchor=tk.W, pady=(0, 10))

        # File inputs
        file_frame = ttk.LabelFrame(main, text="Dosyalar", padding=10)
        file_frame.pack(fill=tk.X, pady=5)

        # DXF
        r1 = ttk.Frame(file_frame)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="DXF Dosyası:", width=15).pack(side=tk.LEFT)
        self.dxf_var = tk.StringVar()
        ttk.Entry(r1, textvariable=self.dxf_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(r1, text="Seç", command=self.select_dxf, width=6).pack(side=tk.RIGHT)

        # TXT
        r2 = ttk.Frame(file_frame)
        r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text="TXT Dosyası:", width=15).pack(side=tk.LEFT)
        self.txt_var = tk.StringVar()
        ttk.Entry(r2, textvariable=self.txt_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(r2, text="Seç", command=self.select_txt, width=6).pack(side=tk.RIGHT)

        # Settings
        set_frame = ttk.LabelFrame(main, text="Ayarlar", padding=10)
        set_frame.pack(fill=tk.X, pady=5)

        r3 = ttk.Frame(set_frame)
        r3.pack(fill=tk.X)

        ttk.Label(r3, text="Öteleme (m):").pack(side=tk.LEFT)
        self.offset_var = tk.StringVar(value="0.20")
        ttk.Entry(r3, textvariable=self.offset_var, width=8).pack(side=tk.LEFT, padx=5)

        ttk.Label(r3, text="Yön:").pack(side=tk.LEFT, padx=(15, 0))
        self.dir_var = tk.StringVar(value="left")
        ttk.Combobox(r3, textvariable=self.dir_var, values=["left", "right"],
                     width=8, state='readonly').pack(side=tk.LEFT, padx=5)

        # Run button
        self.run_btn = ttk.Button(main, text="▶  BAŞLAT", command=self.run, style='Big.TButton')
        self.run_btn.pack(fill=tk.X, pady=10)

        # Progress
        self.progress = ttk.Progressbar(main, mode='indeterminate')
        self.progress.pack(fill=tk.X)

        # Log
        log_frame = ttk.LabelFrame(main, text="İşlem Günlüğü", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, font=('Consolas', 9),
                                                   bg='#1a1a2e', fg='#e0e0e0',
                                                   insertbackground='#e0e0e0')
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def select_dxf(self):
        f = filedialog.askopenfilename(
            title="DXF Dosyası Seçin",
            filetypes=[("DXF Dosyaları", "*.dxf *.DXF"), ("Tüm Dosyalar", "*.*")])
        if f:
            self.dxf_var.set(f)
            # Auto-set TXT path
            base_dir = os.path.dirname(f)
            for fn in os.listdir(base_dir):
                if fn.lower().endswith('.txt') and 'koord' in fn.lower():
                    self.txt_var.set(os.path.join(base_dir, fn))
                    break

    def select_txt(self):
        f = filedialog.askopenfilename(
            title="Koordinat TXT Dosyası Seçin",
            filetypes=[("TXT Dosyaları", "*.txt *.TXT"), ("Tüm Dosyalar", "*.*")])
        if f:
            self.txt_var.set(f)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def run(self):
        dxf = self.dxf_var.get().strip()
        txt = self.txt_var.get().strip()

        if not dxf or not os.path.exists(dxf):
            messagebox.showerror("Hata", "DXF dosyası bulunamadı!")
            return
        if not txt or not os.path.exists(txt):
            messagebox.showerror("Hata", "TXT dosyası bulunamadı!")
            return

        try:
            offset = float(self.offset_var.get())
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz öteleme mesafesi!")
            return

        direction = self.dir_var.get()
        output_dir = os.path.dirname(dxf)

        self.run_btn.configure(state='disabled')
        self.progress.start()
        self.log_text.delete('1.0', tk.END)

        def worker():
            try:
                ncn, dxf_out = process(dxf, txt, output_dir, offset, direction, self.log)
                self.root.after(0, lambda: self.on_done(ncn, dxf_out))
            except Exception as e:
                self.root.after(0, lambda: self.on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def on_done(self, ncn, dxf_out):
        self.progress.stop()
        self.run_btn.configure(state='normal')
        messagebox.showinfo("Tamamlandı!",
                           f"İşlem başarılı!\n\n"
                           f"NCN: {os.path.basename(ncn)}\n"
                           f"DXF: {os.path.basename(dxf_out)}\n\n"
                           f"Dosyalar DXF ile aynı klasöre kaydedildi.")

    def on_error(self, msg):
        self.progress.stop()
        self.run_btn.configure(state='normal')
        self.log(f"\nHATA: {msg}")
        messagebox.showerror("Hata", f"İşlem sırasında hata oluştu:\n{msg}")


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
