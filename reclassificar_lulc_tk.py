#!/usr/bin/env python3
"""
GUI básica para reclassificação de Uso e Cobertura do Solo usando Tkinter.

Atualizações:
- Suporte a arquivo de lookup CSV (delimitado por ';') para preencher a coluna NOME com a coluna 'Descricao' ou 'Description'.
- Campo para escolher tabela de lookup; usa ./lookup_tables/lulc_lookup.csv por padrão se existir.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from util.ler_classes_lulc_csv import ler_classes_lulc_csv

# Tentativa de import opcional para reclassificação real
try:
    import rasterio
    import numpy as np
    HAS_RASTERIO = True
except Exception:
    HAS_RASTERIO = False

class LULCGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Reclassificação de Uso e Cobertura do Solo")
        self.geometry("660x760")
        self.minsize(500, 680)

        self.filepath = tk.StringVar()
        self.savepath = tk.StringVar()
        # lookup CSV path (padrão)
        # default_lookup = os.path.join(os.getcwd(), "rater", "Codigos-da-legenda-colecao-9-LS.csv")
        # self.lookup_path = tk.StringVar(value=default_lookup)
        self.lookup_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Aguardando ação...")
        self.classes = []  # lista de tuples (nome, original_val, new_val)
        self.lookup = {}   # dicionário Class_ID -> row dict

        self._build_ui()

        # se existir lookup padrão, tente carregar (não obrigatório)
        if os.path.isfile(self.lookup_path.get()):
            try:
                self.lookup = ler_classes_lulc_csv(self.lookup_path.get())
                self.status_text.set(f"Lookup carregado: {len(self.lookup)} entradas")
            except Exception:
                # falha silenciosa aqui, será carregado quando usuário clicar
                pass

    def _build_ui(self):
        # Top frame: file selection + lookup selection
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        # Lookup selection (CSV)
        ttk.Label(top, text="Tabela LULC (CSV):").grid(row=0, column=0, sticky="w", pady=(8,0))
        lookup_entry = ttk.Entry(top, textvariable=self.lookup_path, width=50)
        lookup_entry.grid(row=0, column=1, padx=6, pady=(8,0))
        ttk.Button(top, text="Escolher tabela...", command=self.browse_lookup).grid(row=0, column=2, padx=6, pady=(8,0))
        ttk.Button(top, text="Recarregar tabela", command=self.reload_lookup).grid(row=0, column=3, padx=6, pady=(8,0))

        ttk.Label(top, text="CAMINHO LULC:").grid(row=1, column=0, sticky="w")
        entry = ttk.Entry(top, textvariable=self.filepath, width=50)
        entry.grid(row=1, column=1, padx=6)
        ttk.Button(top, text="Escolher...", command=self.browse_file).grid(row=1, column=2, padx=6)
        # Carregar a classes button - após escolher arquivo LULC
        ttk.Button(top, text="Carregar RASTER", command=self.load_classes).grid(row=1, column=3, pady=8, sticky="w")


        # Middle: treeview with classes
        mid = ttk.Frame(self, padding=(10,0,10,0))
        mid.pack(fill="both", expand=True)

        cols = ("nome", "n_classe", "nova_classe")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("nome", text="NOME")
        self.tree.heading("n_classe", text="Nº CLASSE")
        self.tree.heading("nova_classe", text="NOVA CLASSE")

        self.tree.column("nome", width=300, anchor="w")
        self.tree.column("n_classe", width=100, anchor="center")
        self.tree.column("nova_classe", width=120, anchor="center")

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(mid, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        mid.rowconfigure(0, weight=1)
        mid.columnconfigure(0, weight=1)

        # Bind para edição de célula (nova_classe) via duplo clique
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # Reclassificar button
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill="x")

        # Caminho para salvar o arquivo reclassificado
        ttk.Label(btn_frame, text="SALVAR RECLASS.:").grid(row=0, column=0, sticky="w", pady=(12,0))
        save_entry = ttk.Entry(btn_frame, textvariable=self.savepath, width=58)
        save_entry.grid(row=0, column=1, padx=6, pady=(12,0))
        ttk.Button(btn_frame, text="Escolher...", command=self.browse_save).grid(row=0, column=2, padx=6, pady=(12,0))

        # Botão reclassificar
        self.reclass_button = ttk.Button(btn_frame, text="RECLASSIFICAR", command=self.reclassify)
        self.reclass_button.grid(row=1, column=0, columnspan=3, pady=(12,0))


        # Progress and status
        status_frame = ttk.Frame(self, padding=(10,0,10,10))
        status_frame.pack(fill="x")

        self.progress = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(6,6))

        self.status_label = ttk.Label(status_frame, textvariable=self.status_text)
        self.status_label.pack(anchor="w")

    def browse_file(self):
        path = filedialog.askopenfilename(title="Selecione o arquivo LULC (raster)")
        if path:
            self.filepath.set(path)

    def browse_save(self):
        path = filedialog.asksaveasfilename(title="Salvar raster reclassificado como",
                                            defaultextension=".tif",
                                            filetypes=[("GeoTIFF", ".tif"), ("All files", "*.*")])
        if path:
            self.savepath.set(path)

    def browse_lookup(self):
        path = filedialog.askopenfilename(title="Selecione tabela LULC (CSV ';')",
                                          filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.lookup_path.set(path)
            try:
                self.lookup = ler_classes_lulc_csv(path)
                self.status_text.set(f"Lookup carregado: {len(self.lookup)} entradas")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar lookup: {e}")

    def reload_lookup(self):
        path = self.lookup_path.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("Aviso", "Selecione um arquivo de tabela válido primeiro.")
            return
        try:
            self.lookup = ler_classes_lulc_csv(path)
            self.status_text.set(f"Lookup recarregado: {len(self.lookup)} entradas")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao recarregar lookup: {e}")

    def load_classes(self):
        path = self.filepath.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("Aviso", "Selecione um arquivo raster válido primeiro.")
            return

        self.status_text.set("Carregando classes...")
        self.progress["value"] = 0
        self.tree.delete(*self.tree.get_children())
        self.classes.clear()

        # Carrega em thread para não travar GUI (caso demore)
        thread = threading.Thread(target=self._do_load_classes, args=(path,), daemon=True)
        thread.start()

    def _do_load_classes(self, path):
        try:
            # tenta carregar lookup se ainda não carregado e existir caminho
            if not self.lookup:
                lookup_path = self.lookup_path.get().strip()
                if lookup_path and os.path.isfile(lookup_path):
                    try:
                        self.lookup = ler_classes_lulc_csv(lookup_path)
                    except Exception:
                        # não falhar, apenas continuar sem lookup
                        self.lookup = {}

            if HAS_RASTERIO:
                # tenta ler valores únicos do raster (primeira banda)
                with rasterio.open(path) as src:
                    arr = src.read(1, masked=False)  # numpy array
                    vals = np.unique(arr)
                    # remover possíveis nodata
                    if src.nodata is not None:
                        vals = vals[vals != src.nodata]
                    vals = vals.tolist()
                vals_sorted = sorted(vals)
                classes = []
                for v in vals_sorted:
                    # tentar mapear pelo lookup (se inteiro)
                    name = f"Classe {v}"
                    try:
                        vk = int(v)
                        if vk in self.lookup:
                            row = self.lookup[vk]
                            name = (row.get('Descricao') or row.get('Description') or name)
                    except Exception:
                        # se não for convertível, tentar buscar como string chave
                        try:
                            if str(v) in self.lookup:
                                row = self.lookup[str(v)]
                                name = (row.get('Descricao') or row.get('Description') or name)
                        except Exception:
                            pass
                    # new class inicial igual antiga
                    try:
                        new_val = int(v)
                    except Exception:
                        new_val = v
                    classes.append((name, v, new_val))
                self.classes = classes
                self.status_text.set(f"Encontradas {len(classes)} classes.")
            else:
                # Se rasterio não disponível -> criar exemplo
                example = [1,2,3,4,5]
                classes = []
                for i in example:
                    name = f"CLASSE {i}"
                    if i in self.lookup:
                        row = self.lookup[i]
                        name = (row.get('Descricao') or row.get('Description') or name)
                    classes.append((name, i, i))
                self.classes = classes
                self.status_text.set("rasterio não disponível: carregadas classes de exemplo.")
        except Exception as e:
            self.classes = []
            self.status_text.set("Erro carregando classes.")
            messagebox.showerror("Erro", f"Erro ao carregar classes: {e}")
            return

        # Popular a treeview (no thread principal)
        self.after(0, self._populate_tree)

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for name, orig, new in self.classes:
            self.tree.insert("", "end", values=(name, orig, new))
        self.progress["value"] = 100

    def _on_tree_double_click(self, event):
        # Determina coluna e item
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        rowid = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)  # e.g. "#3"
        if not rowid or col != "#3":
            # só tornar editável a coluna "nova_classe" (3ª)
            return

        x, y, width, height = self.tree.bbox(rowid, col)
        value = self.tree.set(rowid, "nova_classe")

        # Cria um Entry temporário sobre a célula
        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, value)
        entry.focus_set()

        def on_enter(event=None):
            new_val = entry.get().strip()
            if new_val == "":
                # não aceita vazio
                messagebox.showwarning("Aviso", "Novo valor não pode ser vazio.")
            else:
                self.tree.set(rowid, "nova_classe", new_val)
                # Atualizar self.classes também
                idx = list(self.tree.get_children()).index(rowid)
                name, orig, _ = self.classes[idx]
                # tenta converter para int se aplicável
                try:
                    new_conv = int(new_val)
                except Exception:
                    new_conv = new_val
                self.classes[idx] = (name, orig, new_conv)
            entry.destroy()

        def on_focus_out(event=None):
            entry.destroy()

        entry.bind("<Return>", on_enter)
        entry.bind("<FocusOut>", on_focus_out)

    def reclassify(self):
        if not self.classes:
            messagebox.showwarning("Aviso", "Carregue as classes antes de reclassificar.")
            return
        out_path = self.savepath.get().strip()
        if not out_path:
            messagebox.showwarning("Aviso", "Escolha um caminho de saída para salvar a reclassificação.")
            return
        in_path = self.filepath.get().strip()
        if not in_path or not os.path.isfile(in_path):
            messagebox.showwarning("Aviso", "Arquivo de entrada inválido.")
            return

        # Desabilita botão e inicia thread
        self.reclass_button.config(state="disabled")
        self.status_text.set("Iniciando reclassificação...")
        self.progress["value"] = 0

        thread = threading.Thread(target=self._do_reclassify, args=(in_path, out_path), daemon=True)
        thread.start()

    def _do_reclassify(self, in_path, out_path):
        try:
            # monta dicionário de mapeamento original -> novo
            mapping = {}
            for name, orig, new in self.classes:
                mapping[orig] = new

            if HAS_RASTERIO:
                # Leitura e escrita real
                with rasterio.open(in_path) as src:
                    profile = src.profile.copy()
                    arr = src.read(1)
                    out_arr = arr.copy()
                    # Aplica mapeamento (suporta números inteiros)
                    for k, v in mapping.items():
                        try:
                            out_arr[arr == k] = v
                        except Exception:
                            # tentativa de igualdade para tipos mistos
                            out_arr[arr == k] = v
                    # Escreve
                    profile.update(dtype=out_arr.dtype)
                    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
                    with rasterio.open(out_path, "w", **profile) as dst:
                        dst.write(out_arr, 1)
                self.after(0, lambda: self._on_reclass_done(success=True, msg="Reclassificação concluída e salva."))
            else:
                # Modo simulado (apenas cria um arquivo texto para demonstrar)
                os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write("SIMULATED RECLASSIFICATION\n")
                    f.write(f"Input: {in_path}\n")
                    f.write("Mapping:\n")
                    for k, v in mapping.items():
                        f.write(f"{k} -> {v}\n")
                self.after(0, lambda: self._on_reclass_done(success=True, msg="Simulação concluída. Arquivo salvo."))
        except Exception as e:
            self.after(0, lambda: self._on_reclass_done(success=False, msg=str(e)))

    def _on_reclass_done(self, success, msg):
        if success:
            self.status_text.set(msg)
            self.progress["value"] = 100
            messagebox.showinfo("Pronto", msg)
        else:
            self.status_text.set("Erro durante reclassificação.")
            messagebox.showerror("Erro", f"Erro ao reclassificar: {msg}")
        self.reclass_button.config(state="normal")


if __name__ == "__main__":
    app = LULCGUI()
    app.mainloop()