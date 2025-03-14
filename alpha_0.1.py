import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import json
import sqlite3
import random
import csv
import time
from PIL import Image, ImageTk
import qrcode




class Turniermanager(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Poker Tourney Manager")
        self.attributes('-fullscreen', True)

        # Initialisiere die Payout-Struktur
        self.payout_structure = {}
        self.load_payout_structure()  # Lädt die Payout-Struktur beim Programmstart

        self.start_points = {}

        # Erstellen Sie eine Instanz von BountyManager
        self.bounty_manager = BountyManager()

        #Initialisiere die Liste der Pokervarianten
        self.poker_variants = self.load_poker_variants()

        # Initialisiere das VariantRoulette mit dem JSON-File
        self.variant_roulette = VariantRoulette("poker_variants.json")

        # Initialisiere den DatabaseManager
        self.db_manager = DatabaseManager()

        self.pause_remaining_time = None
        self.timer_running = False
        self.pause_running = False  # Initialisiere den Pausen-Status als nicht laufend
        self.remaining_time = None
        self.current_level_index = 0
        self.tournament_clock = None
       
        # Initialisiere die Variablen für dynamische Eingabefelder
        self.entry_vars = {}

        # Initialisiere die Liste der Spieler
        self.players = []  # Leere Liste, um sicherzustellen, dass das Attribut existiert
        self.load_players()  # Lade Spieler in self.players

        self.tournament_players = []  # Liste für Turnierspieler
        self.player_widgets = {}  # Dictionary, um Widgets für jeden Spieler zu speichern

        # Notebook für das Hauptfenster und das Turnierfenster
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Tournament Tab erstellen
        self.tournament_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tournament_tab, text="Tourney")

        # Turnieruhr Tab erstellen
        self.tournament_clock_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tournament_clock_tab, text="Clock")

        # Spieler-Frame für dynamische Spieler-Eingabefelder
        self.player_frame = ttk.Frame(self.tournament_tab, borderwidth=2, relief="solid")
        self.player_frame.pack(padx=10, pady=10, fill="x", expand=True)

        # Frame für das Tournament Tab hinzufügen
        self.tournament_frame = ttk.Frame(self.tournament_tab, borderwidth=2, relief="solid")
        self.tournament_frame.pack(padx=10, pady=10, fill="x", expand=True)
        self.create_tournament_widgets()


         # Frame und Widgets für das Turnieruhr Tab hinzufügen
        self.create_tournament_clock_widgets()

        # Starte die automatische Berechnung des Preispools
        self.schedule_prize_pool_calculation()

        # Database Tab erstellen und Widgets hinzufügen
        self.database_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.database_tab, text="Database")
        self.create_database_widgets()

         # Initialisiere die Liste der Turnierspieler
        self.tournament_players = []  # Leere Liste zum Start hinzufügen

        self.check_eliminations()  # Startet die Überwachung der "Eliminiert durch"-Spalte

        self.update_liga_view()
        self.update_year_pot_display()



    def update_bad_beat_jackpot_display(self):
        liga_id = 1  # Beispielhafte Liga-ID
        bad_beat_jackpot = self.db_manager.get_bad_beat_jackpot(liga_id)
        self.bad_beat_jackpot_label.config(text=f"Bad Beat Jackpot: €{bad_beat_jackpot:.2f}")


    def update_bounty_earnings(self):
        """Berechnet und aktualisiert die Bounty Earnings für jeden Spieler basierend auf Knockouts und Bounty-Preis."""
        try:
            # Hole den aktuellen Bounty-Preis aus dem Eingabefeld
            bounty_price = float(self.entry_vars["bounty_price_entry"].get())
        
            for item in self.player_tree.get_children():
                values = self.player_tree.item(item, "values")
                player_name = values[0]
                knockouts = int(values[7])  # Stelle sicher, dass knockouts ein int ist

                # Berechne die Bounty Earnings
                bounty_earnings = knockouts * bounty_price

                # Aktualisiere die Spalte für Bounty Earnings im Treeview
                new_values = list(values)
                new_values[8] = f"{bounty_earnings:.2f}"  # Formatiere auf zwei Dezimalstellen
                self.player_tree.item(item, values=new_values)
            
                # Debugging: Ausgabe zur Überprüfung
                print(f"Bounty Earnings für {player_name}: {bounty_earnings} bei {knockouts} KOs und {bounty_price} Bounty-Preis.")
    
        except ValueError:
            messagebox.showerror("Fehler", "Ungültiger Bounty Preis oder Knockout-Zähler.")


    def check_eliminations(self):
        # Initialisiere das Dictionary für die Knockout-Zähler
        current_knockouts = {player.name: 0 for player in self.tournament_players}
    
        # Überprüfe die "Eliminiert durch"-Spalte für jeden Spieler im Treeview
        for item in self.player_tree.get_children():
            values = self.player_tree.item(item, 'values')
            eliminator_name = values[6]  # Index der "Eliminiert durch"-Spalte im Treeview
            player_name = values[0]
        
            if eliminator_name:  # Prüfe, ob der Spieler eliminiert wurde
                if eliminator_name in current_knockouts:
                    current_knockouts[eliminator_name] += 1

        # Aktualisiere die Knockouts- und Bounty-Earnings-Spalte im Treeview
        for player in self.tournament_players:
            knockouts = current_knockouts.get(player.name, 0)
            bounty_earnings = knockouts * self.bounty_manager.bounty_price  # Berechnung Bounty Earnings

            # Aktualisiere die Spalten für Knockouts und Bounty-Earnings
            for item in self.player_tree.get_children():
                values = self.player_tree.item(item, 'values')
                if values[0] == player.name:
                    # Aktualisiere die Knockouts- und Bounty-Earnings-Spalten (angenommen an Index 7 und 8)
                    new_values = list(values)
                    new_values[7] = knockouts
                    new_values[8] = f"{bounty_earnings:.2f}"  # Bounty Earnings in Euro darstellen
                    self.player_tree.item(item, values=new_values)
                    break

        # Regelmäßiges Überprüfen der Knockouts und Bounty-Werte alle paar Sekunden
        self.after(5000, self.check_eliminations)

        self.update_bounty_earnings()

    def load_poker_variants(self):
        try:
            with open('poker_variants.json', 'r') as file:
                data = json.load(file)
                return data.get("poker_variants", [])
        except FileNotFoundError:
            messagebox.showerror("Error", "The file poker_variants.json was not found.")
            return []
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Error decoding poker_variants.json.")
            return []



    def create_database_widgets(self):
        """Erstellt Widgets für den Database-Tab."""


        # Frame für die Liga-Wertung erstellen
        liga_frame = ttk.Frame(self.database_tab, borderwidth=2, relief="solid")
        liga_frame.pack(padx=10, pady=10)  # Füllt nicht den gesamten Bereich aus

        # Liga Treeview für die Jahreswertung mit einer Erhöhung der Höhe
        self.liga_treeview = ttk.Treeview(liga_frame, columns=("Position", "Player", "Points"), show="headings", height=20)
        self.liga_treeview.heading("Position", text="Position")
        self.liga_treeview.heading("Player", text="Player")
        self.liga_treeview.heading("Points", text="Points")

        # Setze spezifische Spaltenbreiten
        self.liga_treeview.column("Position", width=80)
        self.liga_treeview.column("Player", width=150)
        self.liga_treeview.column("Points", width=100)

        # Füge den Treeview in das Frame ein und lasse ihn den gesamten verfügbaren Raum vertikal ausfüllen
        self.liga_treeview.pack(fill="both", expand=True, padx=10, pady=10)
    
        # Begrenze das Treeview in Höhe und Breite
        self.liga_treeview.pack(fill="both", expand=False, padx=10, pady=10)
    
        # Frame für das zuletzt exportierte Turnierergebnis erstellen
        tournament_frame = ttk.Frame(self.database_tab, borderwidth=2, relief="solid")
        tournament_frame.pack(padx=10, pady=10)  # Füllt nicht den gesamten Bereich aus

        # Treeview für das zuletzt exportierte Turnierergebnis mit den gleichen Spalten wie im Tournament-Tab
        self.tournament_results_treeview = ttk.Treeview(
            tournament_frame, 
            columns=("Name", "Points", "Rebuys", "Add-Ons", "Bonus", "Bust", "Eliminated By", "Knockouts", "Bounty Earnings (€)"),
            show="headings", 
            height=10
        )

        # Spaltenüberschriften und Breite festlegen
        self.tournament_results_treeview.heading("Name", text="Name")
        self.tournament_results_treeview.heading("Points", text="Points")
        self.tournament_results_treeview.heading("Rebuys", text="Rebuys")
        self.tournament_results_treeview.heading("Add-Ons", text="Add-Ons")
        self.tournament_results_treeview.heading("Bonus", text="Bonus")
        self.tournament_results_treeview.heading("Bust", text="Bust")
        self.tournament_results_treeview.heading("Eliminated By", text="Eliminated By")
        self.tournament_results_treeview.heading("Knockouts", text="Knockouts")
        self.tournament_results_treeview.heading("Bounty Earnings (€)", text="Bounty Earnings (€)")

        # Breite für jede Spalte festlegen
        self.tournament_results_treeview.column("Name", width=150)
        self.tournament_results_treeview.column("Points", width=80)
        self.tournament_results_treeview.column("Rebuys", width=80)
        self.tournament_results_treeview.column("Add-Ons", width=80)
        self.tournament_results_treeview.column("Bonus", width=80)
        self.tournament_results_treeview.column("Bust", width=60)
        self.tournament_results_treeview.column("Eliminated By", width=120)
        self.tournament_results_treeview.column("Knockouts", width=80)
        self.tournament_results_treeview.column("Bounty Earnings (€)", width=120)
    
        # Begrenze das Treeview in Höhe und Breite
        self.tournament_results_treeview.pack(fill="both", expand=False, padx=10, pady=10)

        # Label für den Jahrespot
        self.year_pot_label = ttk.Label(liga_frame, text="Jahrespot: €0.00", font=("Helvetica", 48), foreground="green")
        self.year_pot_label.pack(pady=10, anchor="w")

        self.bad_beat_jackpot_label = ttk.Label(liga_frame, text="Bad Beat Jackpot: €0.00", font=("Helvetica", 38), foreground="red")
        self.bad_beat_jackpot_label.pack(pady=10, anchor="w")
        self.update_bad_beat_jackpot_display()

         # Frame für die Buttons erstellen
        button_frame = ttk.Frame(self.database_tab, borderwidth=2, relief="solid")
        button_frame.pack(padx=10, pady=10)  # Entferne fill="x" und expand=True, um die Größe zu begrenzen

        # Button "Export to Database" im Button-Frame hinzufügen
        export_button = ttk.Button(button_frame, text="Export to Database", command=self.export_to_database)
        export_button.pack(side="left", padx=10, pady=10)

        # Button "Export Tournament Results to CSV" im Button-Frame hinzufügen
        export_csv_button = ttk.Button(button_frame, text="Export Tournament Results to CSV", command=self.export_tournament_results_to_csv)
        export_csv_button.pack(side="left", padx=10, pady=10)

        # Button "Undo Last Export" im Button-Frame hinzufügen
        undo_export_button = ttk.Button(button_frame, text="Undo Last Export", command=self.undo_last_export)
        undo_export_button.pack(side="left", padx=10, pady=10)

        # Aktualisierung der Liga-Wertung
        self.update_liga_view()


    # Methode zum Aktualisieren des Bounty-Preises
    def update_bounty_price(self):
        """Aktualisiert den Bounty-Preis und speichert ihn im BountyManager."""
        try:
            price = float(self.entry_vars["bounty_price_entry"].get())
            self.bounty_manager.set_bounty_price(price)
        except ValueError:
            messagebox.showerror("Fehler", "Ungültiger Bounty Preis eingegeben.")

        self.update_bounty_earnings()

    # In der Methode record_knockout
    def record_knockout(self, eliminator_name, eliminated_name):
        eliminator = next((p for p in self.tournament_players if p.name == eliminator_name), None)
        eliminated = next((p for p in self.tournament_players if p.name == eliminated_name), None)
    
        if eliminator and eliminated:
            # Knockout erfassen
            eliminator.increase_knockout()
            self.bounty_manager.record_knockout(eliminator)
        
            # Bounty-Betrag berechnen
            bounty_earnings = self.bounty_manager.calculate_bounty_earnings(eliminator)
        
            # Treeview aktualisieren
            self.update_player_list_display()
        
            messagebox.showinfo("Bounty Update", f"{eliminator.name} hat jetzt {bounty_earnings:.2f} in Bounties.")


    def get_year_pot(self, liga_id):
        result = self.conn.execute("""
            SELECT amount FROM YearPot WHERE liga_id = ?
        """, (liga_id,)).fetchone()
        print(f"Database Year Pot for liga_id {liga_id}: {result}")  # Debug-Ausgabe
        return result[0] if result else 0



    def update_year_pot_display(self):
        liga_id = 1  # Beispielhafte Liga-ID
        year_pot = self.db_manager.get_year_pot(liga_id)
        print(f"Year Pot fetched: {year_pot}")  # Debug-Ausgabe
        self.year_pot_label.config(text=f"Jahrespot: €{year_pot:.2f}")


    def undo_last_export(self):
        """Macht den letzten Export zur Datenbank rückgängig."""
        success = self.db_manager.remove_last_tournament()
        if success:
            messagebox.showinfo("Erfolg", "Letzter Export erfolgreich rückgängig gemacht.")
        
            # Aktualisiere die Jahreswertung und den Jahrespot in der Anzeige
            self.update_liga_view()
            self.update_year_pot_display()
            # Aktualisiere die Anzeige des Bad Beat Jackpots
            self.update_bad_beat_jackpot_display()
        
            # Leere den Treeview für die zuletzt exportierten Turnierergebnisse
            for item in self.tournament_results_treeview.get_children():
                self.tournament_results_treeview.delete(item)
        else:
            messagebox.showerror("Fehler", "Kein vorheriger Export gefunden.")

    def export_tournament_results_to_csv(self):
        """Exportiert die aktuellen Turnierergebnisse aus dem Treeview in eine CSV-Datei."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Tournament Results as CSV"
        )

        if file_path:
            # Hole die Daten aus dem Treeview
            columns = ["Name", "Position", "Points", "Rebuys", "Add-Ons", "Bonus", "Bust", "eliminated_by"]
            data = []
        
            for index, item in enumerate(self.player_tree.get_children(), start=1):
                values = self.player_tree.item(item, "values")
                data.append((values[0], index, *values[1:]))  # index für Position, restliche Werte aus values

            # Schreibe die Daten in die CSV-Datei
            with open(file_path, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(columns)  # Spaltenüberschriften schreiben
                writer.writerows(data)    # Daten schreiben

            messagebox.showinfo("Erfolg", f"Turnierergebnisse erfolgreich in {file_path} exportiert.")


    def create_tournament_clock_widgets(self):
        """Erstellt Widgets für den Turnieruhr-Tab."""
    
        # Hauptframe für den Turnieruhr-Tab, aufgeteilt in zwei Spalten
        clock_frame = ttk.Frame(self.tournament_clock_tab, borderwidth=2, relief="solid")
        clock_frame.pack(padx=10, pady=10, fill="both", expand=True)
    
        # Frame für die linke Seite (Timer, Level-Infos, Preispool)
        left_column = ttk.Frame(clock_frame)
        left_column.grid(row=0, column=0, padx=10, pady=10, sticky="n")
    
        # Frame für die rechte Seite (Steuerung, Treeview, Varianten Roulette)
        right_column = ttk.Frame(clock_frame)
        right_column.grid(row=0, column=1, padx=10, pady=10, sticky="n")

        # Timer-Anzeige im linken Bereich
        timer_frame = ttk.Frame(left_column, borderwidth=2)
        timer_frame.pack(pady=20)
        self.timer_display_label = ttk.Label(timer_frame, text="00:00", font=("Helvetica", 280), foreground="orange")
        self.timer_display_label.pack(pady=20)

        # Anzeige des aktuellen und nächsten Levels und Blinds
        self.level_blinds_label = ttk.Label(left_column, text="Level: - | Blinds: -", font=("Helvetica", 100), foreground="lightblue")
        self.level_blinds_label.pack(pady=10)
        self.next_level_blinds_label = ttk.Label(left_column, text="Next Level: - | Blinds: -", font=("Helvetica", 60), foreground="lightblue")
        self.next_level_blinds_label.pack(pady=5)
        self.pause_timer_label = ttk.Label(left_column, text="Break: --:--", font=("Helvetica", 100), foreground="magenta")
        self.pause_timer_label.pack(pady=10)
        self.pause_timer_label.pack_forget()  # Versteckt, bis es benötigt wird
        self.pause_countdown_label = ttk.Label(left_column, text="Pause in: --:--", font=("Helvetica", 60))
        self.pause_countdown_label.pack(pady=10)
       

        # Preispool und Durchschnittlicher Chipstapel
        self.prize_stack_frame = ttk.Frame(left_column, borderwidth=2, relief="groove")
        self.prize_stack_frame.pack(pady=10, padx=10, fill="x")
        self.prize_pool_label = ttk.Label(self.prize_stack_frame, text="Prize Pool: --", font=("Helvetica", 32), foreground="green", justify="center", anchor="center")
        self.prize_pool_label.pack(pady=5, fill="x", expand=True)
        self.avg_chipstack_label = ttk.Label(self.prize_stack_frame, text="Avg Chipstack: --", font=("Helvetica", 32), foreground="green", justify="center", anchor="center")
        self.avg_chipstack_label.pack(pady=5, fill="x", expand=True)

        # Steuerungselemente im rechten Bereich
        control_frame = ttk.Frame(right_column, borderwidth=2, relief="groove")
        control_frame.pack(pady=10, anchor="center")
        button_container = ttk.Frame(control_frame)
        button_container.pack(pady=10)
        self.start_timer_button = ttk.Button(button_container, text="Start / Resume Clock", command=self.start_tournament_clock)
        self.start_timer_button.pack(side="left", padx=5, pady=5)
        self.pause_timer_button = ttk.Button(button_container, text="Pause Clock", command=self.pause_tournament_clock)
        self.pause_timer_button.pack(side="left", padx=5, pady=5)
        self.prev_level_button = ttk.Button(button_container, text="Previous Level", command=self.prev_level)
        self.prev_level_button.pack(side="left", padx=5, pady=5)
        self.next_level_button = ttk.Button(button_container, text="Next Level", command=self.next_level)
        self.next_level_button.pack(side="left", padx=5, pady=5)

        # Frame für den Treeview im Clock Tab
        clock_player_frame = ttk.Frame(right_column, width=700)
        clock_player_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Treeview für die Spieler im Clock Tab, mit einer erhöhten Höhe für mehr Einträge
        self.clock_player_tree = ttk.Treeview(
            clock_player_frame,
            columns=("name", "points", "rebuys", "addon", "bonus", "bust", "Eliminated By"),
            show="headings",
            height=20  # Erhöht die Anzahl der sichtbaren Einträge
        )

        # Spaltenüberschriften definieren und die Breite für jede Spalte festlegen
        self.clock_player_tree.heading("name", text="Name")
        self.clock_player_tree.heading("points", text="Punkte")
        self.clock_player_tree.heading("rebuys", text="Rebuys")
        self.clock_player_tree.heading("addon", text="Add-On")
        self.clock_player_tree.heading("bonus", text="Bonus")
        self.clock_player_tree.heading("bust", text="Bust")
        self.clock_player_tree.heading("Eliminated By", text="Eliminiert durch")

        # Spaltenbreite anpassen
        self.clock_player_tree.column("name", width=100)
        self.clock_player_tree.column("points", width=60)
        self.clock_player_tree.column("rebuys", width=60)
        self.clock_player_tree.column("addon", width=70)
        self.clock_player_tree.column("bonus", width=70)
        self.clock_player_tree.column("bust", width=60)
        self.clock_player_tree.column("Eliminated By", width=120)

        # Treeview-Element mit "both" für fill und "expand" für die vertikale Ausdehnung platzieren
        self.clock_player_tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Erstelle den Frame für Statistiken unter dem Treeview-Frame
        stats_frame_clock = ttk.Frame(right_column, borderwidth=2, relief="solid")
        stats_frame_clock.pack(padx=10, pady=10, fill="x")  # Pack ohne Expand, um unter dem Treeview zu erscheinen

        # Verwende grid, um die Labels und Eingabefelder nebeneinander anzuordnen
        ttk.Label(stats_frame_clock, text="Rebuys:", font=("Helvetica", 16)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        rebuys_entry_clock = ttk.Entry(stats_frame_clock, font=("Helvetica", 16), textvariable=self.entry_vars["rebuys_entry"], width=5)
        rebuys_entry_clock.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(stats_frame_clock, text="Add-Ons:", font=("Helvetica", 16)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        addons_entry_clock = ttk.Entry(stats_frame_clock, font=("Helvetica", 16), textvariable=self.entry_vars["addons_entry"], width=5)
        addons_entry_clock.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(stats_frame_clock, text="Bonus:", font=("Helvetica", 16)).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        bonus_entry_clock = ttk.Entry(stats_frame_clock, font=("Helvetica", 16), textvariable=self.entry_vars["bonus_entry"], width=5)
        bonus_entry_clock.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(stats_frame_clock, text="Number of Players:", font=("Helvetica", 16)).grid(row=3, column=0, sticky="w", padx=10, pady=5)
        tournament_player_count_entry_clock = ttk.Entry(stats_frame_clock, font=("Helvetica", 16), width=5, textvariable=self.tournament_player_count_var)
        tournament_player_count_entry_clock.grid(row=3, column=1, padx=10, pady=5)

        # "Varianten Roulette" Frame
        self.roulette_frame = ttk.Frame(right_column, borderwidth=2, relief="solid")
        self.roulette_frame.pack(pady=10, padx=10, anchor="s")
        variants_roulette_button = ttk.Button(self.roulette_frame, text="Variante Roulette", command=self.spin_variant_roulette)
        variants_roulette_button.grid(row=0, column=0, padx=10, pady=10)
        self.variant_label = ttk.Label(self.roulette_frame, text="Random Game", font=("Helvetica", 16))
        self.variant_label.grid(row=0, column=1, padx=10, pady=10)

         # Pause-Steuerungselemente
        pause_control_frame = ttk.Frame(right_column, borderwidth=2, relief="groove")
        pause_control_frame.pack(pady=10)
        self.pause_resume_button = ttk.Button(pause_control_frame, text="Stop / Resume Pause", command=self.toggle_pause_timer)
        self.pause_resume_button.pack(side="left", padx=5, pady=5)
        self.end_pause_button = ttk.Button(pause_control_frame, text="End Pause", command=self.end_pause)
        self.end_pause_button.pack(side="left", padx=5, pady=5)


    def display_tournament_results(self):
        """Zeigt die zuletzt exportierten Turnierergebnisse im Treeview an."""
        # Entferne alle Einträge aus dem Turnierergebnis-Treeview
        for item in self.tournament_results_treeview.get_children():
            self.tournament_results_treeview.delete(item)

        # Hole die Daten aus der Spieler-Turnierliste und füge sie in den Treeview ein
        for player in self.tournament_players:
            position = self.tournament_players.index(player) + 1
            self.tournament_results_treeview.insert("", "end", values=(
                player.name,
                position,
                player.points,
                player.rebuys,
                player.addon,
                player.bonus
            ))

    def get_last_tournament_results(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT Spieler.name, TurnierErgebnisse.punkte
            FROM TurnierErgebnisse
            JOIN Spieler ON TurnierErgebnisse.spieler_id = Spieler.id
            ORDER BY TurnierErgebnisse.turnier_id DESC
        """)
        return cursor.fetchall()



    def prev_level(self):
        """Wechselt zum vorigen Level und startet es."""
        if self.current_level_index > 0:
            self.current_level_index -= 1
            self.set_current_level()
            # Aktualisiere den Pause-Countdown
            self.pause_remaining_time = self.calculate_time_until_next_pause()
            self.update_pause_countdown()
        else:
            messagebox.showinfo("Info", "Bereits im ersten Level.")

    def next_level(self):
        """Wechselt zum nächsten Level und startet es."""
        if self.current_level_index < len(self.tournament_clock.levels) - 1:
            self.current_level_index += 1
            self.set_current_level()
            # Aktualisiere den Pause-Countdown
            self.pause_remaining_time = self.calculate_time_until_next_pause()
            self.update_pause_countdown()
        else:
            messagebox.showinfo("Info", "Bereits im letzten Level.")

    def set_current_level(self):
        """Setzt das aktuelle Level und startet den Timer neu."""
        if self.tournament_clock:
            self.current_level_data = self.tournament_clock.levels[self.current_level_index]
            self.remaining_time = self.current_level_data["duration"] * 60
            self.update_level_blinds_display()
        
            # Aktualisiere die verbleibende Pausezeit und setze den Countdown neu
            self.pause_remaining_time = self.calculate_time_until_next_pause()
            self.update_pause_countdown()  # Countdown zur nächsten Pause starten
            self.update_timer_display()

    def update_timer_display(self):
        """Aktualisiert das Timer-Display basierend auf der verbleibenden Zeit."""
        minutes, seconds = divmod(self.remaining_time, 60)
        self.timer_display_label.config(text=f"{minutes:02}:{seconds:02}")


    def load_players(self):
        """Lädt Spieler aus einer JSON-Datei und speichert sie in self.players."""
        try:
            with open("players.json", "r") as file:
                players_data = json.load(file)
                self.players = []
                for player_data in players_data:
                    name = list(player_data.keys())[0]  # Extrahiere den Namen des Spielers
                    details = player_data
                    player = Player(
                        name=name,
                        points=details.get("points", 0),
                        rebuys=details.get("rebuys", 0),
                        addon=details.get("addon", False),
                        bonus=details.get("bonus", False),
                        bust=details.get("bust", False)
                    )
                    self.players.append(player)
        except FileNotFoundError:
            messagebox.showerror("Error", "Die Datei 'players.json' wurde nicht gefunden.")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Fehler beim Lesen der Datei 'players.json'.")

    def add_player_to_tournament(self):
        player_name = self.player_combobox.get()
        if player_name:
            player = next((p for p in self.players if p.name == player_name), None)
            if player and player not in self.tournament_players:
                self.tournament_players.append(player)
                self.update_player_list_display()
                self.update_tournament_player_count()
            
                # Spieler zur GUI hinzufügen
                self.add_player_controls(player)

                # Dropdown-Menüs aktualisieren
                self.update_eliminated_by_dropdowns()
            else:
                messagebox.showinfo("Info", f"{player_name} ist bereits im Turnier.")
        else:
            messagebox.showwarning("Warnung", "Bitte wählen Sie einen Spieler aus.")


    def spin_variant_roulette(self):
        # Wähle eine Variante und aktualisiere das Label
        selected_variant = self.variant_roulette.spin()
        self.variant_label.config(
            text=f"{selected_variant}",
            font=("Helvetica", 70, "bold"),  # Schriftgröße auf 20 und fett
            foreground="red"  # Textfarbe auf Rot setzen
        )



    def create_tournament_widgets(self):
        """Erstellt Widgets für das Tournament Tab."""
        # Frame für das Tournament Tab
        self.tournament_frame = ttk.Frame(self.tournament_tab, borderwidth=2, relief="solid")
        self.tournament_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Erstelle einen neuen Frame für die Spieler-Auswahl und -Buttons
        player_selection_frame = ttk.Frame(self.tournament_frame, borderwidth=2, relief="solid")
        player_selection_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

        # Auswahlbox für Spieler
        player_names = [player.name for player in self.players]
        #self.player_combobox = ttk.Combobox(player_selection_frame, values=player_names, font=("Helvetica", 16))
        #self.player_combobox.grid(row=0, column=0, padx=10, pady=10)

        # Hinzufügen des Eingabefelds
        self.player_name_entry = ttk.Entry(player_selection_frame, font=("Helvetica", 16))
        self.player_name_entry.grid(row=0, column=0, padx=10, pady=10)

        # Button zum Hinzufügen eines Spielers
        add_player_button = ttk.Button(player_selection_frame, text="Add Player", command=self.add_player_to_tournament)
        add_player_button.grid(row=0, column=1, padx=10, pady=10)

        # Button zum Entfernen eines Spielers
        remove_player_button = ttk.Button(player_selection_frame, text="Remove Player", command=self.remove_player_from_tournament)
        remove_player_button.grid(row=0, column=2, padx=10, pady=10)

        style = ttk.Style()
        style.configure("Treeview", rowheight=25)  # Höhe der Zeilen, um größere Schrift anzupassen
        style.configure("Treeview", font=("Helvetica", 16))  # Schriftgröße für die Einträge
        style.configure("Treeview.Heading", font=("Helvetica", 14, "bold"))  # Schriftgröße für Überschriften

        # In der create_tournament_widgets-Methode die neuen Spalten hinzufügen
        self.player_tree = ttk.Treeview(self.tournament_frame, columns=("name", "points", "rebuys", "addon", "bonus", "bust", "Eliminated By", "knockouts", "bounty"), show="headings", height=15)

        # Spaltenüberschriften und Breite definieren
        self.player_tree.heading("name", text="Name")
        self.player_tree.heading("points", text="Punkte")
        self.player_tree.heading("rebuys", text="Rebuys")
        self.player_tree.heading("addon", text="Add-On")
        self.player_tree.heading("bonus", text="Bonus")
        self.player_tree.heading("bust", text="Bust")
        self.player_tree.heading("Eliminated By", text="Eliminiert durch")
        self.player_tree.heading("knockouts", text="Knockouts")
        self.player_tree.heading("bounty", text="Bounty Earnings (€)")

        # Spaltenbreite anpassen
        self.player_tree.column("name", width=100)
        self.player_tree.column("points", width=60)
        self.player_tree.column("rebuys", width=60)
        self.player_tree.column("addon", width=70)
        self.player_tree.column("bonus", width=70)
        self.player_tree.column("bust", width=60)
        self.player_tree.column("Eliminated By", width=120)
        self.player_tree.column("knockouts", width=70)
        self.player_tree.column("bounty", width=100)

        # Treeview-Element platzieren
        self.player_tree.grid(row=4, column=0, columnspan=3, padx=10, pady=(10, 20), sticky="nsew")

        # Frame für den Info-Bereich
        self.info_frame = ttk.Frame(self.tournament_frame, borderwidth=2, relief="solid")
        self.info_frame.grid(row=5, column=1, padx=10, pady=10, sticky="n")

        # Definiere die Felder für den Zustand in einem Dictionary
        fields = {
            "startstack_entry": (0, 0),
            "rebuystack_entry": (1, 0),
            "addonstack_entry": (2, 0),
            "bonus_chips_entry": (3, 0),
            "rebuy_entry": (1, 2),
            "addon_entry": (2, 2),
            "buy_in_entry": (0, 2),
            "yearpot_entry": (3, 2),
            "bounty_price_entry": (4,2),
            "bad_beat_jackpot_entry": (4,0)
        }
    
        # Labels und Entries dynamisch erstellen und in `self.entry_vars` speichern
        for var_name, (row, col) in fields.items():
            label_text = var_name.replace("_entry", "").replace("_", " ").title() + ":"
            ttk.Label(self.info_frame, text=label_text, font=("Helvetica", 16)).grid(row=row, column=col, padx=10, pady=5, sticky="w")
            entry_var = tk.StringVar()
            entry = ttk.Entry(self.info_frame, font=("Helvetica", 16), width=5, textvariable=entry_var)
            entry.grid(row=row, column=col+1, padx=10, pady=5, sticky="w")
            entry_var.set("0")  # Standardwert setzen
            self.entry_vars[var_name] = entry_var

        # Buttons zum Speichern und Laden des Zustands
        save_state_button = ttk.Button(self.info_frame, text="Save Config", command=self.save_current_state)
        save_state_button.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        load_state_button = ttk.Button(self.info_frame, text="Load Config", command=self.load_previous_state)
        load_state_button.grid(row=5, column=1, padx=10, pady=5, sticky="w")

        # Tourney Structure und Load Payouts Buttons hinzufügen
        structure_button = ttk.Button(self.info_frame, text="Blind Structure", command=self.load_blind_file)
        structure_button.grid(row=5, column=2, padx=10, pady=5, sticky="w")

        # Frame für Statistiken wie Rebuys, Add-Ons, Bonus und Anzahl der Spieler
        stats_frame = ttk.Frame(self.tournament_frame, borderwidth=2, relief="solid")
        stats_frame.grid(row=4, column=3, padx=10, pady=10, sticky="n")

        # Rebuys-Anzeige
        ttk.Label(stats_frame, text="Rebuys:", font=("Helvetica", 16)).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.entry_vars["rebuys_entry"] = tk.StringVar(value="0")
        rebuys_entry = ttk.Entry(stats_frame, font=("Helvetica", 16), textvariable=self.entry_vars["rebuys_entry"], width=5)
        rebuys_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Add-Ons-Anzeige
        ttk.Label(stats_frame, text="Add-Ons:", font=("Helvetica", 16)).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.entry_vars["addons_entry"] = tk.StringVar(value="0")
        addons_entry = ttk.Entry(stats_frame, font=("Helvetica", 16), textvariable=self.entry_vars["addons_entry"], width=5)
        addons_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Bonus-Anzeige
        ttk.Label(stats_frame, text="Bonus:", font=("Helvetica", 16)).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.entry_vars["bonus_entry"] = tk.StringVar(value="0")
        bonus_entry = ttk.Entry(stats_frame, font=("Helvetica", 16), textvariable=self.entry_vars["bonus_entry"], width=5)
        bonus_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Spielerzählung
        ttk.Label(stats_frame, text="Number of Players:", font=("Helvetica", 16)).grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.tournament_player_count_var = tk.StringVar(value="0")
        tournament_player_count_entry = ttk.Entry(stats_frame, font=("Helvetica", 16), width=5, textvariable=self.tournament_player_count_var)
        tournament_player_count_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        self.entry_vars["player_count_entry"] = self.tournament_player_count_var

        # Frame für das Logo erstellen
        logo_frame = ttk.Frame(self.tournament_frame, borderwidth=2, relief="solid")
        logo_frame.grid(row=5, column=2, padx=10, pady=10, sticky="w")

        # Logo laden und skalieren
        original_image = Image.open("logo.png")
        resized_image = original_image.resize((180, 180), Image.LANCZOS)  # Verwenden Sie LANCZOS zum Antialiasing
        self.logo_image = ImageTk.PhotoImage(resized_image)

        # Button erstellen und ins grid-Layout einsetzen
        logo_button = tk.Button(logo_frame, image=self.logo_image, borderwidth=0, highlightthickness=0, command=self.show_qr_code)
        logo_button.grid(row=0, column=0, padx=10, pady=10)

        self.remaining_players_var = tk.StringVar(value="0")
      
    
    def update_bounty_mode(self):
        """Aktualisiert den Bounty-Modus basierend auf der Auswahl und passt Berechnungen an."""
        mode = self.bounty_mode.get()
        if mode == "normal":
            print("Normaler Bounty Modus aktiviert.")
            # Rufen Sie hier die Berechnungen für den normalen Bounty-Modus auf
        elif mode == "progressive":
            print("Progressiver Bounty Modus aktiviert.")
            # Hier können Sie die Berechnungen für den progressiven Bounty-Modus hinzufügen


    def add_player_controls(self, player):
        """Erstellt Bedienelemente für die Eigenschaften eines Spielers und fügt sie in die GUI ein."""
        row = len(self.tournament_players) + 6  # Dynamische Zeile nach bestehenden Elementen
        player_controls = {}

        # Label für den Spielernamen
        ttk.Label(self.tournament_frame, text=player.name, font=("Helvetica", 16)).grid(row=row, column=0, padx=10, pady=5, sticky="w")

        # Eingabefeld für Rebuys
        rebuys_var = tk.IntVar(value=player.rebuys)
        rebuys_entry = ttk.Entry(self.tournament_frame, textvariable=rebuys_var, font=("Helvetica", 16), width=5)
        rebuys_entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        player_controls["rebuys"] = rebuys_var

        # Add-On Checkbox
        addon_var = tk.BooleanVar(value=player.addon)
        addon_check = ttk.Checkbutton(self.tournament_frame, variable=addon_var, text="Add-On")
        addon_check.grid(row=row, column=2, padx=10, pady=5, sticky="w")
        player_controls["addon"] = addon_var

        # Bonus Checkbox
        bonus_var = tk.BooleanVar(value=player.bonus)
        bonus_check = ttk.Checkbutton(self.tournament_frame, variable=bonus_var, text="Bonus")
        bonus_check.grid(row=row, column=3, padx=10, pady=5, sticky="w")
        player_controls["bonus"] = bonus_var

        # Bust Checkbox
        bust_var = tk.BooleanVar(value=player.bust)
        bust_check = ttk.Checkbutton(self.tournament_frame, variable=bust_var, text="Bust", 
                                 command=lambda: self.toggle_eliminated_by(player, bust_var))
        bust_check.grid(row=row, column=4, padx=10, pady=5, sticky="w")
        player_controls["bust"] = bust_var

        # Dropdown-Menü für "Eliminiert durch" (immer sichtbar)
        elim_by_var = tk.StringVar(value="")
        elim_by_combobox = ttk.Combobox(self.tournament_frame, textvariable=elim_by_var, font=("Helvetica", 16), width=15)
        elim_by_combobox['values'] = [p.name for p in self.tournament_players if p != player]
        elim_by_combobox.grid(row=row, column=5, padx=10, pady=5, sticky="w")
        player_controls["eliminated_by"] = elim_by_combobox

        # Speichere den Namen des Spielers, der den Spieler eliminiert hat
        elim_by_var.trace("w", lambda *args: setattr(player, "eliminated_by", elim_by_var.get()))
    
        # Speichere die Widgets für den Spieler
        self.player_controls[player.name] = player_controls


    def toggle_eliminated_by(self, player, bust_var):
        """Zeigt das Dropdown-Menü an oder verbirgt es und aktualisiert den KO-Zähler des eliminierenden Spielers."""
        controls = self.player_controls[player.name]
        elim_by_combobox = controls["eliminated_by"]
        elim_by_var.trace_add("write", lambda *args, name=player.name, elim=elim_by_var: self.record_knockout(name, elim.get()))

        if bust_var.get():  # Spieler als "Bust" markiert
            elim_by_combobox.grid()  # Dropdown-Menü anzeigen
            elim_by_combobox['values'] = [p.name for p in self.tournament_players if p != player]
        
            # Binde die Auswahl, um die Knockout-Aufzeichnung zu aktualisieren
            elim_by_combobox.bind("<<ComboboxSelected>>", lambda event: self.record_knockout(elim_by_var, player.name))
        
            # Initialen Wert direkt prüfen
            if elim_by_var:
                self.record_knockout(elim_by_var, player.name)
        else:  # Spieler ist nicht mehr "Bust"
            elim_by_combobox.grid_remove()  # Dropdown-Menü verbergen
            elim_by_var = ""  # Auswahl zurücksetzen

            # Reset the Player's eliminator if they're brought back
            player.eliminated_by = ""
            if player in self.tournament_players:
                player.knockout = 0
                player.bounty = 0  # Bounty auf 0 setzen

        # Treeview aktualisieren
        self.update_player_list_display()

    def on_eliminator_selected(self, player, eliminator_name):
        """Verarbeitet die Auswahl eines Eliminators und aktualisiert den KO-Zähler und die Bounty-Einnahmen."""
        # Erfasse den Knockout für den ausgewählten Eliminator
        if eliminator_name:
            self.record_knockout(eliminator_name, player.name)
            player.eliminated_by = eliminator_name  # Speichere den Eliminator
    
        # Aktualisiere den Treeview
        self.update_player_list_display()


    def update_ko_count(self, player, eliminated_by_name):
        """Aktualisiert den KO-Zähler des eliminierenden Spielers und speichert die 'Eliminiert durch'-Information."""
        eliminated_by_player = next((p for p in self.tournament_players if p.name == eliminated_by_name), None)
        if eliminated_by_player:
            eliminated_by_player.knockouts += 1
            player.eliminated_by = eliminated_by_name  # Speichert, wer den Spieler eliminiert hat

        # Aktualisiere die Anzeige im Treeview
        self.update_player_list_display()

   
    def add_player_to_tournament(self):
        player_name = self.player_name_entry.get()
        if player_name:
            # Überprüfen, ob der Spieler bereits im Turnier ist
            if any(p.name == player_name for p in self.tournament_players):
                messagebox.showinfo("Info", f"{player_name} ist bereits im Turnier.")
                return

            # Erstellen eines neuen Spielers mit Standardattributen
            player = Player(
                name=player_name,
                points=0,
                rebuys=0,
                addon=False,
                bonus=False,
                bust=False,
                knockout=False,
                eliminated_by=""
            )

            self.tournament_players.append(player)
            self.update_player_list_display()
            self.update_tournament_player_count()

            # Aktualisiere die Anzahl der verbleibenden Spieler
            if not hasattr(self, 'remaining_players_var'):
                self.remaining_players_var = tk.StringVar()
            self.remaining_players_var.set(len(self.tournament_players))

            # Bestimme Zeile und Spalte basierend auf der Spieleranzahl
            player_index = len(self.tournament_players) - 1  # Nullbasierter Index
            row = player_index % 8  # Zeilenwechsel nach jeweils 8 Spielern
            col = (player_index // 8) * 7  # Spaltenwechsel nach 8 Spielern

            # Spielername
            player_name_label = ttk.Label(self.player_frame, text=player.name, font=("Helvetica", 16))
            player_name_label.grid(row=row, column=col, padx=10, pady=5, sticky="w")

            # Rebuys Label
            rebuys_label = ttk.Label(self.player_frame, text="Rebuys:", font=("Helvetica", 16))
            rebuys_label.grid(row=row, column=col + 1, padx=10, pady=5, sticky="w")

            # Rebuys Entry
            rebuys_var = tk.StringVar()
            rebuys_var.set(str(player.rebuys))
            rebuys_var.trace("w", lambda *args, p=player, rv=rebuys_var: self.update_player_rebuys(p, rv))
            player_rebuys_entry = ttk.Entry(self.player_frame, textvariable=rebuys_var, width=5, font=("Helvetica", 16))
            player_rebuys_entry.grid(row=row, column=col + 2, padx=10, pady=5, sticky="w")

            # Add-On Checkbox
            addon_var = tk.BooleanVar(value=player.addon)
            addon_var.trace("w", lambda *args, p=player, v=addon_var: self.update_player_addon(p, v))
            addon_checkbox = ttk.Checkbutton(self.player_frame, variable=addon_var, text="Add-On")
            addon_checkbox.grid(row=row, column=col + 3, padx=10, pady=5, sticky="w")

            # Bonus Checkbox
            bonus_var = tk.BooleanVar(value=player.bonus)
            bonus_var.trace("w", lambda *args, p=player, v=bonus_var: self.update_player_bonus(p, v))
            bonus_checkbox = ttk.Checkbutton(self.player_frame, variable=bonus_var, text="Bonus")
            bonus_checkbox.grid(row=row, column=col + 4, padx=10, pady=5, sticky="w")

            # Bust Checkbox
            bust_var = tk.BooleanVar(value=player.bust)
            bust_var.trace("w", lambda *args, p=player, v=bust_var: self.update_player_bust(p, v))
            bust_checkbox = ttk.Checkbutton(self.player_frame, variable=bust_var, text="Bust")
            bust_checkbox.grid(row=row, column=col + 5, padx=10, pady=5, sticky="w")

            # Dropdown für "Eliminiert durch" mit Standardwert
            elim_by_var = tk.StringVar(value="Eliminiert durch")
            elim_by_combobox = ttk.Combobox(self.player_frame, textvariable=elim_by_var, font=("Helvetica", 16), width=15)

            # Füge den Standardwert und die anderen Spielernamen hinzu
            player_names = ["Eliminiert durch"] + [p.name for p in self.tournament_players if p != player]
            elim_by_combobox['values'] = player_names

            elim_by_combobox.grid(row=row, column=col + 6, padx=10, pady=5, sticky="w")

            # Speichere Widgets
            self.player_widgets[player.name] = (player_name_label, player_rebuys_entry, addon_checkbox, bonus_checkbox, bust_checkbox, elim_by_combobox)

            # Aktualisiere das Dropdown für alle Spieler
            self.update_eliminated_by_dropdowns()

            # Eingabefeld leeren
            self.player_name_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Warnung", "Bitte geben Sie einen Spielernamen ein.")

       

    def update_totals(self):
        """Aktualisiert die Gesamtwerte für Rebuys, Add-Ons und Bonus auf der GUI."""
        total_rebuys = sum(player.rebuys for player in self.tournament_players)
        total_addons = sum(1 for player in self.tournament_players if player.addon)
        total_bonus = sum(1 for player in self.tournament_players if player.bonus)
    
        # Aktualisiere die GUI Felder
        self.entry_vars["rebuys_entry"].set(str(total_rebuys))
        self.entry_vars["addons_entry"].set(str(total_addons))
        self.entry_vars["bonus_entry"].set(str(total_bonus))


    def update_player_bust(self, player, bust_var):
        """Aktualisiert den Bust-Status des Spielers, sortiert ihn im Treeview und passt den durchschnittlichen Chipstapel an."""
        player.bust = bust_var.get()

        # Hole die gespeicherten Widgets für diesen Spieler
        widgets = self.player_widgets.get(player.name)
        if widgets:
            # Extrahiere das Dropdown-Menü-Widget (angenommen, es ist das letzte in der Widgets-Tuple)
            _, _, _, _, _, elim_by_combobox = widgets

            # Wenn der Spieler als "Bust" markiert ist, trage den gewählten Spieler aus dem Dropdown-Menü ein
            if player.bust:
                eliminator_name = elim_by_combobox.get()  # Hole den gewählten Namen
                if eliminator_name and eliminator_name != "Eliminiert durch":
                    player.eliminated_by = eliminator_name
                else:
                    player.eliminated_by = ""  # Keine Auswahl, Feld bleibt leer

                # Entferne den Spieler aus der Liste und füge ihn an der richtigen Position am Ende wieder ein
                if player in self.tournament_players:
                    self.tournament_players.remove(player)
            
                # Berechne die neue Position für den Bust-Status
                bust_count = sum(1 for p in self.tournament_players if p.bust)
                new_position = len(self.tournament_players) - bust_count
                self.tournament_players.insert(new_position, player)
            
                # Weisen Sie die Punkte basierend auf der Bust-Position zu
                player.points = bust_count + 1  # Erster Bust erhält 1 Punkt, der nächste 2 Punkte, usw.
        
            else:
                # Spieler ist nicht mehr Bust: Setze Punkte auf 0 und sortiere ihn nach oben
                player.points = 0
                player.eliminated_by = ""  # Entferne den Eliminator-Eintrag, wenn der Spieler wieder aktiv wird
            
                # Entferne ihn von der aktuellen Position und füge ihn oben bei den aktiven Spielern wieder ein
                if player in self.tournament_players:
                    self.tournament_players.remove(player)
                self.tournament_players.insert(0, player)  # Fügt ihn oben in die Liste der nicht-bust-Spieler ein

            # Aktualisiere die Anzeige im Treeview
            self.update_player_list_display()

        self.calculate_prize_pool()  # Preispool und durchschnittlicher Chipstapel neu berechnen

    def update_player_rebuys(self, player, rebuys_var):
        """Aktualisiert die Rebuys des Spielers und die Anzeige im Treeview."""
        try:
            # Setze den Rebuys-Wert für den Spieler basierend auf der Eingabe
            player.rebuys = int(rebuys_var.get())
        
            # Aktualisiere den Treeview nur mit den Rebuys und berühre die Knockouts nicht
            for item in self.player_tree.get_children():
                values = self.player_tree.item(item, "values")
                if values[0] == player.name:
                    # Ersetze nur den Rebuys-Wert im Treeview, lass Knockouts unverändert
                    new_values = list(values)
                    new_values[2] = player.rebuys  # Index 2 steht für Rebuys
                    self.player_tree.item(item, values=new_values)
                    break

            # Aktualisiere nur die Totals für Rebuys und andere Felder
            self.update_totals()
        except ValueError:
            # Fehlerbehandlung bei ungültiger Eingabe
            return

    def update_player_addon(self, player, addon_var):
        player.addon = addon_var.get()
        self.update_player_tree(player)
        self.update_player_list_display()  # Füge dies hinzu, um den Treeview zu aktualisieren
        self.update_totals()  # Aktualisiere die Gesamtsummen

    def update_player_bonus(self, player, bonus_var):
        player.bonus = bonus_var.get()
        self.update_player_tree(player)
        self.update_player_list_display()  # Füge dies hinzu, um den Treeview zu aktualisieren
        self.update_totals()  # Aktualisiere die Gesamtsummen


    def update_player_tree(self, player):
        """Aktualisiert die Anzeige des Spielers im Treeview."""
        for item in self.player_tree.get_children():
            if self.player_tree.item(item, "values")[0] == player.name:
                self.player_tree.item(item, values=(player.name, player.points, player.rebuys, player.addon, player.bonus, player.bust, player.eliminated_by))
                break

    def update_eliminated_by_dropdowns(self):
        """Aktualisiert die 'Eliminiert durch' Dropdown-Menüs für alle Spieler im Turnier."""
        for player in self.tournament_players:
            # Nur Spieler, die noch aktiv im Turnier sind (nicht gebustet)
            remaining_players = [p.name for p in self.tournament_players if p != player and not p.bust]
        
            # Finde das entsprechende Dropdown-Menü für diesen Spieler
            controls = self.player_widgets.get(player.name, {})
            if controls:
                elim_by_combobox = controls[5]  # Das Dropdown-Menü befindet sich an der 6. Position in der Liste
                elim_by_combobox['values'] = remaining_players  # Setze nur die verbliebenen Spieler als Auswahl


    def remove_player_from_tournament(self):
        selected_item = self.player_tree.selection()
        if selected_item:
            player_name = self.player_tree.item(selected_item, 'values')[0]
            player = next((p for p in self.tournament_players if p.name == player_name), None)
            if player:
                self.tournament_players.remove(player)
                self.update_player_list_display()
                self.update_tournament_player_count()
                self.remove_player_controls(player)
                self.update_eliminated_by_dropdowns()
                self.remaining_players_var.set(len(self.tournament_players))  # Aktualisiere die verbleibenden Spieler
            else:
                messagebox.showerror("Fehler", "Spieler nicht gefunden.")
        else:
            messagebox.showwarning("Warnung", "Bitte wählen Sie einen Spieler aus der Liste aus.")

    def remove_player_controls(self, player):
        """Entfernt die GUI-Elemente eines Spielers."""
        widgets = self.player_widgets.get(player.name)
        if widgets:
            for widget in widgets:
                widget.destroy()
            del self.player_widgets[player.name]

    def create_player_widgets(self, player):
        """Erstellt Eingabefelder für spezifische Spieler im player_frame und speichert sie."""
        row = len(self.tournament_players)  # Position im player_frame
        rebuys_label = ttk.Label(self.player_frame, text=f"{player.name} Rebuys:", font=("Helvetica", 14))
        rebuys_entry = ttk.Entry(self.player_frame, font=("Helvetica", 14), width=5)
        
        rebuys_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        rebuys_entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        
        # Speichere die Widgets für den Spieler, damit sie entfernt werden können
        self.player_widgets[player.name] = (rebuys_label, rebuys_entry)


    def clear_player_widgets(self, player):
        """Löscht die Widgets des spezifischen Spielers vom player_frame."""
        if player.name in self.player_widgets:
            for widget in self.player_widgets[player.name]:
                widget.grid_forget()
                widget.destroy()
            del self.player_widgets[player.name]

    def update_tournament_player_count(self):
        """Aktualisiert die Anzahl der Turnierspieler im Tournament Tab."""
        count = len(self.tournament_players)
        self.tournament_player_count_var.set(str(count))


    def update_player_list_display(self):
        for tree in [self.player_tree, self.clock_player_tree]:
            for i in tree.get_children():
                tree.delete(i)

            for player in self.tournament_players:
                bounty_earnings = self.bounty_manager.calculate_bounty_earnings(player)
                tree.insert("", "end", values=(
                    player.name,
                    player.points,
                    player.rebuys,
                    player.addon,
                    player.bonus,
                    player.bust,
                    player.eliminated_by,
                    player.knockout,
                    f"{bounty_earnings:.2f}"
                ))
            

    def load_blind_file(self):
        # Öffne die Datei mit der Turnierstruktur
        file_path = filedialog.askopenfilename(title="Select Blind Levels JSON File", filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                    self.tournament_clock = TournamentClock(data)
                    self.current_level_index = 0
                    self.update_level_blinds_display()  # Aktualisierung nach dem Laden
                    print("Turnierstruktur erfolgreich geladen")
                    messagebox.showinfo("Success", f"Structure loaded successfully")
            except json.JSONDecodeError:
                messagebox.showerror("Error", "The JSON file could not be decoded.")


    def start_pause_timer(self):
        """Startet den Pause-Timer und zählt die Pausenzeit herunter."""
        # Stelle sicher, dass kein anderer Timer aktiv ist
        self.timer_running = False
        if hasattr(self, 'timer_id'):
            self.after_cancel(self.timer_id)  # Lösche den Timer des Levels, wenn er noch aktiv ist

        self.pause_timer_label.pack()  # Zeige das Pausen-Label an
        self.timer_display_label.pack_forget()  # Verstecke den normalen Timer (macht ihn unsichtbar)

        # Pause-Dauer aus der Turnierstruktur holen
        self.pause_duration = self.tournament_clock.next_pause_duration * 60
        self.pause_remaining_time = self.pause_duration

        # Starte die Pause-Zählung
        self.update_pause_timer()

    def update_pause_timer(self):
        """Aktualisiert den Pause-Timer und zeigt nach Ablauf wieder die Turnier-Uhr an."""
        if hasattr(self, 'pause_timer_id'):
            self.after_cancel(self.pause_timer_id)  # Vorherige Timer entfernen, um Dopplung zu vermeiden

        if self.pause_remaining_time > 0:
            minutes, seconds = divmod(self.pause_remaining_time, 60)
            self.pause_timer_label.config(text=f"Pause: {minutes:02}:{seconds:02}")
            self.pause_remaining_time -= 1
            self.pause_timer_id = self.after(1000, self.update_pause_timer)
        else:
            # Wenn die Pause beendet ist
            self.pause_timer_label.pack_forget()  # Mache das Pausen-Label unsichtbar
            self.timer_display_label.pack()  # Zeige den normalen Timer wieder an
            self.pause_countdown_label.config(text="Next Break in: --:--")
        
            # Erhöhe das Level nach der Pause und setze die korrekten Werte
            self.current_level_index += 1
            self.timer_running = True
            self.set_next_level_timer()  # Starte das nächste Level mit aktualisierten Anzeigen

    def set_next_level_timer(self):
        """Startet den nächsten Level-Timer und stellt sicher, dass die verbleibende Zeit und Anzeigen korrekt sind."""
        if self.current_level_index < len(self.tournament_clock.levels):
            # Setze das aktuelle Level
            self.current_level_data = self.tournament_clock.levels[self.current_level_index]
            self.remaining_time = self.current_level_data["duration"] * 60  # Setze die Dauer des nächsten Levels
        
            # Aktualisiere die Anzeigen für aktuelles und nächstes Level
            self.update_level_blinds_display()  # Aktualisiere aktuelle und nächste Blinds und Level
            self.pause_remaining_time = self.calculate_time_until_next_pause()
            self.update_pause_countdown()  # Aktualisiere Countdown zur nächsten Pause

            # Starte den Timer für das nächste Level
            self.update_timer_display()  # Zeige die korrekte Zeit an
            self.update_timer()  # Starte den Timer

    def update_timer(self):
        """Aktualisiert den Turnier-Timer und wechselt bei 0 zum nächsten Level oder zur Pause."""
        if hasattr(self, 'timer_id'):
            self.after_cancel(self.timer_id)  # Entferne vorherige Timer, um Wiederholungen zu vermeiden

        if self.remaining_time > 0 and self.timer_running:
            minutes, seconds = divmod(self.remaining_time, 60)
            self.timer_display_label.config(text=f"{minutes:02}:{seconds:02}")
            self.remaining_time -= 1
            self.timer_id = self.after(1000, self.update_timer)
        else:
            # Level ist zu Ende, also Pause oder nächstes Level
            self.current_level_index += 1
            if self.current_level_index < len(self.tournament_clock.levels):
                if str(self.current_level_index) in self.tournament_clock.pauses:
                    self.pause_duration = self.tournament_clock.pauses[str(self.current_level_index)] * 60
                    self.start_pause_timer()
                else:
                    self.set_next_level_timer()  # Gehe direkt zum nächsten Level ohne Pause
            else:
                self.timer_display_label.config(text="Turnierende")
                self.timer_running = False
                print("Turnier beendet")

    def update_pause_countdown(self):
        """Aktualisiert den Countdown bis zur nächsten Pause und zählt korrekt nur einmal pro Sekunde herunter."""
        if hasattr(self, 'pause_timer_id'):
            self.after_cancel(self.pause_timer_id)  # Verhindert das Starten von mehrfachen Timern
    
        if self.pause_remaining_time is not None and self.pause_remaining_time > 0:
            minutes, seconds = divmod(self.pause_remaining_time, 60)
            self.pause_countdown_label.config(text=f"Next Break in: {minutes:02}:{seconds:02}")
            # Verringere die verbleibende Zeit nur um 1 und setze den Countdown nur alle 1000 ms
            self.pause_remaining_time -= 1
            self.pause_timer_id = self.after(1000, self.update_pause_countdown)
        elif self.pause_remaining_time == 0:
            self.pause_countdown_label.config(text="Pause")
            self.start_pause_timer()
        else:
            # Keine weiteren Pausen
            self.pause_countdown_label.config(text="Keine weitere Pause")


    def calculate_prize_pool(self):
        """Berechnet den Preispool und zeigt das Ergebnis im Tournament Tab an."""
        try:
            # Daten aus den Eingabefeldern holen
            num_players = int(self.entry_vars["player_count_entry"].get())
            buy_in = float(self.entry_vars["buy_in_entry"].get())
            rebuy = int(self.entry_vars["rebuy_entry"].get())
            rebuys = int(self.entry_vars["rebuys_entry"].get())
            addon = int(self.entry_vars["addon_entry"].get())
            addons = int(self.entry_vars["addons_entry"].get())
            startstack = int(self.entry_vars["startstack_entry"].get())
            rebuy_stack = int(self.entry_vars["rebuystack_entry"].get())
            addon_stack = int(self.entry_vars["addonstack_entry"].get())
            bonus_chips = int(self.entry_vars["bonus_chips_entry"].get())
            bonus_entry_value = int(self.entry_vars["bonus_entry"].get())

            # Berechnung der verbleibenden Spieler (aktive Spieler, die nicht "Bust" sind)
            remaining_players = sum(1 for player in self.tournament_players if not player.bust)

            # Berechnung des Preispools
            total_buy_in = buy_in * num_players
            total_rebuys = rebuy * rebuys
            total_addon = addon * addons
            total_prize_pool = total_buy_in + total_rebuys + total_addon

            # Berechnung des durchschnittlichen Chipstapels für verbleibende Spieler
            if remaining_players > 0:
                avg_chip_stack = (bonus_chips * bonus_entry_value +
                                num_players * startstack + 
                                rebuys * rebuy_stack + 
                                addons * addon_stack) / remaining_players
            else:
                avg_chip_stack = 0

            # Struktur des Preispools basierend auf der Anzahl der Spieler
            prize_structure = ""
            if str(num_players) in self.payout_structure:
                payouts = self.payout_structure[str(num_players)]
                prize_distribution = [total_prize_pool * percentage for percentage in payouts]
            
                # Formatieren der Preispool-Verteilung
                for i, amount in enumerate(prize_distribution, start=1):
                    prize_structure += f"{i}. Platz: €{amount:.2f}\n"
            else:
                # Falls keine Verteilung für die Spieleranzahl vorhanden ist
                prize_structure = "No payout structure available"

            # Labels für den Preispool und den durchschnittlichen Chipstapel im Turnier-Tab anzeigen
            self.prize_pool_label.config(text=f"Preispool: €{total_prize_pool:.2f}\n{prize_structure}")
            self.avg_chipstack_label.config(text=f"Avg. Chipstack: {avg_chip_stack:.2f}")

        except ValueError:
            messagebox.showerror("Eingabefehler", "Bitte alle Felder korrekt ausfüllen.")

    def schedule_prize_pool_calculation(self):
        """Plant die Preispool-Berechnung alle 10 Sekunden neu."""
        self.calculate_prize_pool()
        self.after(10000, self.schedule_prize_pool_calculation)  # Alle 10 Sekunden (10000 Millisekunden)

    def save_current_state(self):
        """Speichert den aktuellen Zustand in einer JSON-Datei mit benutzerdefiniertem Namen."""
        # Zustand mit allen aktuellen Werten der StringVars speichern, ohne die Spieleranzahl
        state = {entry: var.get() for entry, var in self.entry_vars.items() if entry != "player_count_entry"}
    
        # Bounty Price hinzufügen
        state["bounty_price"] = self.entry_vars["bounty_price_entry"].get()

        # Bad Beat Jackpot hinzufügen
        state["bad_beat_jackpot"] = self.entry_vars["bad_beat_jackpot_entry"].get()
    
        # Dialogfeld zum Speichern öffnen
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save Tournament State"
        )
    
        if file_path:
            try:
                with open(file_path, "w") as file:
                    json.dump(state, file)
                messagebox.showinfo("Success", f"State saved successfully to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred while saving: {str(e)}")
        else:
            messagebox.showinfo("Cancelled", "Save operation was cancelled.")


    def load_previous_state(self):
        """Lädt den gespeicherten Zustand aus einer JSON-Datei mit benutzerdefiniertem Namen."""
        # Dialogfeld zum Öffnen einer Datei
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Load Tournament State"
        )
    
        if file_path:
            try:
                with open(file_path, "r") as file:
                    state = json.load(file)
                
                    # Werte laden und in die StringVars einfügen, ohne die Spieleranzahl
                    for entry, value in state.items():
                        if entry in self.entry_vars:
                            self.entry_vars[entry].set(value)

                    # Bounty Price aus JSON laden und setzen
                    if "bounty_price" in state:
                        self.entry_vars["bounty_price_entry"].set(state["bounty_price"])
                
                    # Bounty Price aus JSON laden und setzen
                    if "bounty_price" in state:
                        self.entry_vars["bounty_price_entry"].set(state["bounty_price"])
                
                    messagebox.showinfo("Success", f"Default Stackes loaded successfully")
            except FileNotFoundError:
                messagebox.showerror("Error", "The selected file could not be found.")
            except json.JSONDecodeError:
                messagebox.showerror("Error", "The selected file is not a valid JSON file.")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
        else:
            messagebox.showinfo("Cancelled", "Load operation was cancelled.")


    def calculate_time_until_next_pause(self):
        """Berechnet die verbleibende Zeit bis zur nächsten Pause ab dem aktuellen Level."""
        remaining_time = 0
        pause_level_found = False  # Überprüfung auf das nächste Pausenlevel
        for i in range(self.current_level_index, len(self.tournament_clock.levels)):
            level_info = self.tournament_clock.levels[i]
            remaining_time += level_info.get("duration", 0) * 60
            # Wenn das nächste Pausenlevel gefunden ist, breche die Schleife
            if str(i + 1) in self.tournament_clock.pauses:
                pause_level_found = True
                break
        # Wenn keine Pause gefunden wurde, setze die Zeit auf None
        return remaining_time if pause_level_found else None

    def start_tournament_clock(self):
        """Startet den Turnier-Timer oder setzt ihn fort."""
        if not self.tournament_clock:
            messagebox.showerror("Fehler", "Turnierstruktur nicht geladen.")
            return

        if not self.timer_running:
            if self.remaining_time is None:
                # Setze die Zeit auf die Dauer des aktuellen Levels, nur wenn sie nicht definiert ist
                self.current_level_data = self.tournament_clock.levels[self.current_level_index]
                self.remaining_time = self.current_level_data["duration"] * 60
                self.pause_remaining_time = self.calculate_time_until_next_pause()

            self.timer_running = True
            self.update_timer()
            self.update_pause_countdown()
            print(f"Turnieruhr gestartet mit {self.remaining_time // 60} Minuten für Level {self.current_level_data['level']}")

    def pause_tournament_clock(self):
        """Pausiert den Turnier- und Pause-Timer."""
        if self.timer_running:
            self.timer_running = False
            if hasattr(self, 'timer_id'):
                self.after_cancel(self.timer_id)
            if hasattr(self, 'pause_timer_id'):
                self.after_cancel(self.pause_timer_id)
            print("Turnieruhr pausiert")


    def toggle_pause_timer(self):
        """Stoppt die Pause und setzt sie fort, falls sie bereits gestoppt wurde."""
        if self.pause_running:
            # Pausiere den Pausen-Timer und speichere die verbleibende Zeit
            if hasattr(self, 'pause_timer_id'):
                self.after_cancel(self.pause_timer_id)
            self.pause_running = False
            print(f"Pause gestoppt bei {self.pause_remaining_time} Sekunden verbleibend")
        else:
            # Setze den Pausen-Timer an der verbleibenden Zeit fort
            self.pause_running = True
            self.update_pause_timer()
            print("Pause fortgesetzt")

    def end_pause(self):
        """Beendet die Pause manuell und startet das nächste Level."""
        # Pausetimer beenden und ausblenden
        if hasattr(self, 'pause_timer_id'):
            self.after_cancel(self.pause_timer_id)  # Stoppe den Pausen-Timer vollständig
        self.pause_timer_label.pack_forget()  # Verstecke das Pausen-Label

        # Überprüfen, ob noch weitere Level vorhanden sind
        if self.current_level_index < len(self.tournament_clock.levels) - 1:
            self.current_level_index += 1  # Zum nächsten Level übergehen
            self.current_level_data = self.tournament_clock.levels[self.current_level_index]
        
            # Setze die verbleibende Zeit für den nächsten Blind-Timer
            self.remaining_time = self.current_level_data["duration"] * 60  # Dauer in Sekunden
        
            # Aktualisiere die Anzeige des aktuellen Levels und Blinds
            self.update_level_blinds_display()

            # Zeige den Turnier-Timer an und starte ihn
            self.timer_display_label.pack()  # Blind-Timer einblenden
            self.timer_running = True  # Timer als laufend setzen
            self.update_timer()  # Starte den Timer für das nächste Level

            # Aktualisiere die Zeit bis zur nächsten Pause
            self.pause_remaining_time = self.calculate_time_until_next_pause()
            self.update_pause_countdown()

            # Debugging-Ausgaben für Überprüfung
            print(f"Pause manuell beendet. Next Level: {self.current_level_index}, Blinds: {self.current_level_data['blinds']}")
        else:
            # Wenn keine weiteren Level vorhanden sind
            messagebox.showinfo("Info", "Turnierende erreicht. Keine weiteren Level.")
            self.timer_display_label.config(text="Turnierende")  # Timer entsprechend anzeigen

    def update_level_blinds_display(self):
        """Aktualisiert die Anzeige für das aktuelle und das nächste Level mit den Blinds."""
        if self.tournament_clock:
            # Aktuelles Level und Blinds
            current_level_data = self.tournament_clock.levels[self.current_level_index]
            level = current_level_data["level"]
            blinds = current_level_data["blinds"]
            self.level_blinds_label.config(text=f"Level: {level} | Blinds: {blinds}")

            # Nächstes Level und Blinds
            next_level_index = self.current_level_index + 1
            if next_level_index < len(self.tournament_clock.levels):
                next_level_data = self.tournament_clock.levels[next_level_index]
                next_level = next_level_data["level"]
                next_blinds = next_level_data["blinds"]
                self.next_level_blinds_label.config(text=f"Next Level: {next_level} | Blinds: {next_blinds}")
            else:
                self.next_level_blinds_label.config(text="Next Level: - | Blinds: -")

    def load_payout_structure(self):
        """Lädt die Preispoolverteilung aus der Datei payout_structure.json und speichert sie in einer Variablen."""
        try:
            with open("payout_structure.json", "r") as file:
                self.payout_structure = json.load(file)
                print("Payout structure loaded successfully.")
        except FileNotFoundError:
            messagebox.showerror("Error", "Die Datei 'payout_structure.json' wurde nicht gefunden.")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Fehler beim Lesen der Datei 'payout_structure.json'.")

    def update_liga_view(self):
        # Jahreswertung für das aktuelle Jahr laden
        current_year = datetime.now().year
        liga_data = self.db_manager.get_liga_summary(current_year)
        print("Liga Data:", liga_data)  # Debug-Ausgabe

        # Treeview leeren und neu befüllen
        for i in self.liga_treeview.get_children():
            self.liga_treeview.delete(i)

        # Sortiere die Spieler nach Punkten und füge sie mit Positionen hinzu
        sorted_liga_data = sorted(liga_data, key=lambda x: x[1], reverse=True)

        # Füge Spieler mit Positionen und Punktänderungen in das Treeview ein
        for position, (player, current_points, previous_points) in enumerate(sorted_liga_data, start=1):
            # Fallback für previous_points, falls dieser None ist
            points_change = current_points - (previous_points if previous_points is not None else 0)
            print(f"Player: {player}, Current Points: {current_points}, Previous Points: {previous_points}, Points Change: {points_change}")
            self.liga_treeview.insert("", "end", values=(position, player, current_points, points_change))

        self.update_year_pot_display()


    def export_to_database(self):
        # Exportiere die Turnierergebnisse in die Datenbank
        datum = datetime.now().strftime("%Y-%m-%d")
        liga_id = 1  # Beispiel-Liga-ID
        self.db_manager.add_tournament(liga_id, datum)
        turnier_id = self.db_manager.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Berechne den Bad Beat Jackpot basierend auf dem Eingabefeld und der Spieleranzahl
        try:
            bad_beat_value = float(self.entry_vars["bad_beat_jackpot_entry"].get())
            num_players = len(self.player_tree.get_children())
            total_bad_beat_jackpot = bad_beat_value * num_players
        except ValueError:
            messagebox.showerror("Fehler", "Ungültiger Wert im Bad Beat Jackpot Feld.")
            return

        # Füge den Bad Beat Jackpot zur Datenbank hinzu
        self.db_manager.add_bad_beat_jackpot(liga_id, total_bad_beat_jackpot)

        # Aktualisiere die Anzeige des Bad Beat Jackpots
        self.update_bad_beat_jackpot_display()


        # Berechne den Year Pot basierend auf dem Eingabefeld und der Spieleranzahl
        try:
            year_pot_value = float(self.entry_vars["yearpot_entry"].get())
            num_players = len(self.player_tree.get_children())
            total_year_pot = year_pot_value * num_players
        except ValueError:
            messagebox.showerror("Fehler", "Ungültiger Wert im Year Pot Feld.")
            return

        # Berechne den Year Pot
        last_added_pot = year_pot_value * num_players

        # Füge den Year Pot hinzu und speichere den zuletzt hinzugefügten Wert
        self.db_manager.add_year_pot(liga_id, last_added_pot)
        self.db_manager.store_last_added(liga_id, last_added_pot)

        # Leere den `tournament_results_treeview` vor dem Export
        for item in self.tournament_results_treeview.get_children():
            self.tournament_results_treeview.delete(item)

        # Exportiere die Spieler und deren Parameter in die TurnierErgebnisse-Tabelle
        for item in self.player_tree.get_children():
            # Hole alle Werte aus dem `player_tree` 
            values = self.player_tree.item(item, "values")
            spieler_name = values[0]
            punkte = int(values[1])
            rebuys = int(values[2])
            # Konvertiere `add_ons` und `bonus` falls sie 'False' oder 'True' sind
            add_ons = int(values[3]) if isinstance(values[3], (int, float)) else (1 if values[3] == 'True' else 0)
            bonus = int(values[4]) if isinstance(values[4], (int, float)) else (1 if values[4] == 'True' else 0)
            bust = 1 if values[5] == 'True' else 0  # Konvertiere 'True'/'False' in 1/0
            eliminated_by = values[6]
            knockouts = int(values[7])
            bounty_earnings = float(values[8])
    
            spieler_id = self.db_manager.get_spieler_id_by_name(spieler_name)

            # Füge den Eintrag mit allen Parametern in die Datenbank hinzu
            self.db_manager.add_tournament_result(
                turnier_id, spieler_id, punkte, rebuys, add_ons, bonus, bust, eliminated_by, knockouts, bounty_earnings
            )

            # Füge die gleichen Werte in den `tournament_results_treeview` des `Database`-Tabs ein
            self.tournament_results_treeview.insert("", "end", values=values)

            self.update_liga_view()
            self.update_year_pot_display()

    def show_qr_code(self):
        # Beispiel-Adresse
        qr_code = LightningQRCode(self, "muffledbeam28@walletofsatoshi.com")
        qr_code.show_qr_window()


    def record_knockout(self, eliminator_name, eliminated_name):
        eliminator = next((p for p in self.tournament_players if p.name == eliminator_name), None)
        eliminated = next((p for p in self.tournament_players if p.name == eliminated_name), None)

        if eliminator and eliminated:
            # Füge Knockout zum Eliminator hinzu
            eliminator.knockout += 1
            # Bounty-Einnahmen basierend auf dem aktuellen Bounty-Preis berechnen
            eliminator.bounty += self.bounty_manager.bounty_price

            # Debug-Ausgabe zur Überprüfung
            print(f"Neuer Stand für {eliminator.name}: {eliminator.knockout} Knockouts, Bounty: {eliminator.bounty:.2f}")
    
            # Anzeige aktualisieren
            self.update_player_list_display()
    
            messagebox.showinfo("Bounty Update", f"{eliminator.name} hat jetzt {eliminator.bounty:.2f} in Bounties.")

    



class DatabaseManager:
    def __init__(self, db_name="poker_tournament.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            # Spieler Tabelle
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS Spieler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            """)

            
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS BadBeatJackpot (
                    liga_id INTEGER PRIMARY KEY,
                    amount REAL DEFAULT 0,
                    FOREIGN KEY (liga_id) REFERENCES Liga(spieler_id)
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS LastBadBeatExport (
                    liga_id INTEGER PRIMARY KEY,
                    amount REAL DEFAULT 0,
                    FOREIGN KEY (liga_id) REFERENCES Liga(spieler_id)
                )
            """)



            # Liga Tabelle - speichert Punkte pro Spieler und Jahr
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS Liga (
                    spieler_id INTEGER,
                    jahr INTEGER NOT NULL,
                    gesamtpunkte INTEGER DEFAULT 0,
                    PRIMARY KEY (spieler_id, jahr),
                    FOREIGN KEY (spieler_id) REFERENCES Spieler(id)
                )
            """)

            # Turnier Tabelle - speichert jedes Turnier mit Liga-ID und Datum
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS Turnier (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    liga_id INTEGER NOT NULL,
                    datum TEXT,
                    FOREIGN KEY (liga_id) REFERENCES Liga(spieler_id)
                )
            """)

            # Turnier Ergebnisse Tabelle - speichert Spielergebnisse für jedes Turnier mit zusätzlichen Parametern
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS TurnierErgebnisse (
                    turnier_id INTEGER,
                    spieler_id INTEGER,
                    punkte INTEGER,
                    rebuys INTEGER DEFAULT 0,
                    add_ons INTEGER DEFAULT 0,
                    bonus INTEGER DEFAULT 0,
                    bust INTEGER DEFAULT 0,
                    eliminated_by TEXT,
                    knockouts INTEGER DEFAULT 0,
                    bounty_earnings REAL DEFAULT 0.0,
                    PRIMARY KEY (turnier_id, spieler_id),
                    FOREIGN KEY (turnier_id) REFERENCES Turnier(id),
                    FOREIGN KEY (spieler_id) REFERENCES Spieler(id)
                )
            """)

            # YearPot Tabelle - speichert den Pot pro Liga-Jahr
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS YearPot (
                    liga_id INTEGER PRIMARY KEY,
                    amount REAL DEFAULT 0,
                    FOREIGN KEY (liga_id) REFERENCES Liga(spieler_id)
                )
            """)

            # Tabelle für den letzten Export
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS LastExport (
                    liga_id INTEGER PRIMARY KEY,
                    amount REAL DEFAULT 0,
                    FOREIGN KEY (liga_id) REFERENCES Liga(spieler_id)
                )
            """)

    def get_spieler_id_by_name(self, spieler_name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM Spieler WHERE name = ?", (spieler_name,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            cursor.execute("INSERT INTO Spieler (name) VALUES (?)", (spieler_name,))
            return cursor.lastrowid  # Neu erstellte Spieler-ID

    def add_tournament(self, liga_id, datum):
        with self.conn:
            self.conn.execute("""
                INSERT INTO Turnier (liga_id, datum)
                VALUES (?, ?)
            """, (liga_id, datum))

    def add_tournament_result(self, turnier_id, spieler_id, punkte, rebuys=0, add_ons=0, bonus=0, bust=0, eliminated_by=None, knockouts=0, bounty_earnings=0.0):
        # Aktualisiert die TurnierErgebnisse und fügt Punkte zur Liga-Tabelle hinzu
        with self.conn:
            # Füge Spielerpunkte und andere Parameter in das Turnier ein
            self.conn.execute("""
                INSERT INTO TurnierErgebnisse (turnier_id, spieler_id, punkte, rebuys, add_ons, bonus, bust, eliminated_by, knockouts, bounty_earnings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (turnier_id, spieler_id, punkte, rebuys, add_ons, bonus, bust, eliminated_by, knockouts, bounty_earnings))

            # Aktualisiere die Liga-Punkte
            self.conn.execute("""
                INSERT INTO Liga (spieler_id, jahr, gesamtpunkte)
                VALUES (?, strftime('%Y', 'now'), ?)
                ON CONFLICT(spieler_id, jahr) DO UPDATE SET
                gesamtpunkte = gesamtpunkte + ?
            """, (spieler_id, punkte, punkte))

    

    def get_bad_beat_jackpot(self, liga_id):
        """Holt den Bad Beat Jackpot für eine spezifische Liga-ID aus der Datenbank."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT amount FROM BadBeatJackpot WHERE liga_id = ?", (liga_id,))
        result = cursor.fetchone()
        return result[0] if result else 0  # Falls kein Eintrag vorhanden ist, gib 0 zurück


    def get_liga_summary(self, year):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT Spieler.name, Liga.gesamtpunkte, PreviousLiga.gesamtpunkte
            FROM Liga
            JOIN Spieler ON Liga.spieler_id = Spieler.id
            LEFT JOIN Liga AS PreviousLiga 
            ON Liga.spieler_id = PreviousLiga.spieler_id 
            AND PreviousLiga.jahr = ? - 1
            WHERE Liga.jahr = ?
            ORDER BY Liga.gesamtpunkte DESC
        """, (year, year))
        return cursor.fetchall()

    def remove_last_tournament(self):
        with self.conn:
            cursor = self.conn.cursor()

            # Finde das zuletzt hinzugefügte Turnier
            cursor.execute("SELECT id, liga_id FROM Turnier ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()

            if result:
                last_tournament_id, liga_id = result

                # Ziehe die Punkte für jeden Spieler in der Liga ab
                cursor.execute("SELECT spieler_id, punkte FROM TurnierErgebnisse WHERE turnier_id = ?", (last_tournament_id,))
                results = cursor.fetchall()
                for spieler_id, punkte in results:
                    cursor.execute("""
                        UPDATE Liga 
                        SET gesamtpunkte = gesamtpunkte - ?
                        WHERE spieler_id = ? AND jahr = strftime('%Y', 'now')
                    """, (punkte, spieler_id))

                # Ziehe den letzten hinzugefügten Year Pot-Wert zurück
                cursor.execute("SELECT amount FROM LastExport WHERE liga_id = ?", (liga_id,))
                last_added_pot = cursor.fetchone()[0] or 0
                cursor.execute("""
                    UPDATE YearPot 
                    SET amount = amount - ?
                    WHERE liga_id = ?
                """, (last_added_pot, liga_id))
                cursor.execute("DELETE FROM LastExport WHERE liga_id = ?", (liga_id,))

                # Ziehe den letzten hinzugefügten Bad Beat Jackpot-Wert zurück
                cursor.execute("SELECT amount FROM LastBadBeatExport WHERE liga_id = ?", (liga_id,))
                last_bad_beat = cursor.fetchone()[0] or 0
                cursor.execute("""
                    UPDATE BadBeatJackpot 
                    SET amount = amount - ?
                    WHERE liga_id = ?
                """, (last_bad_beat, liga_id))
                cursor.execute("DELETE FROM LastBadBeatExport WHERE liga_id = ?", (liga_id,))

                # Entferne das Turnier und die Turnierergebnisse
                cursor.execute("DELETE FROM TurnierErgebnisse WHERE turnier_id = ?", (last_tournament_id,))
                cursor.execute("DELETE FROM Turnier WHERE id = ?", (last_tournament_id,))

                self.conn.commit()
                return True
            else:
                return False

    def add_year_pot(self, liga_id, total_year_pot):
        with self.conn:
            self.conn.execute("""
                INSERT INTO YearPot (liga_id, amount)
                VALUES (?, ?)
                ON CONFLICT(liga_id) DO UPDATE SET amount = amount + ?
            """, (liga_id, total_year_pot, total_year_pot))

    def get_year_pot(self, liga_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT amount FROM YearPot WHERE liga_id = ?", (liga_id,))
        result = cursor.fetchone()
        return result[0] if result else 0  # Falls kein Eintrag vorhanden ist, gib 0 zurück

    def store_last_added(self, liga_id, amount):
        with self.conn:
            self.conn.execute("""
                INSERT INTO LastExport (liga_id, amount)
                VALUES (?, ?)
                ON CONFLICT(liga_id) DO UPDATE SET amount = ?
            """, (liga_id, amount, amount))

    def add_bad_beat_jackpot(self, liga_id, total_bad_beat_jackpot):
        with self.conn:
            self.conn.execute("""
                INSERT INTO BadBeatJackpot (liga_id, amount)
                VALUES (?, ?)
                ON CONFLICT(liga_id) DO UPDATE SET amount = amount + ?
            """, (liga_id, total_bad_beat_jackpot, total_bad_beat_jackpot))

            # Speichere den letzten hinzugefügten Bad Beat Jackpot-Wert
            self.conn.execute("""
                INSERT INTO LastBadBeatExport (liga_id, amount)
                VALUES (?, ?)
                ON CONFLICT(liga_id) DO UPDATE SET amount = ?
            """, (liga_id, total_bad_beat_jackpot, total_bad_beat_jackpot))


    def close(self):
        if self.conn:
            self.conn.close()


class TournamentClock:
    def __init__(self, data):
        self.levels = data["levels"]
        self.pauses = data.get("pauses", {})
        
        # Zusätzliche Attribute für Detailinformationen
        self.current_level = 0
        self.total_levels = len(self.levels)
        self.current_blinds = self.levels[self.current_level].get("blinds", "N/A")
        self.current_duration = self.levels[self.current_level].get("duration", 0)
        self.next_pause_level, self.next_pause_duration = self.get_next_pause_info()

    def get_next_pause_info(self):
        """Findet die nächste Pause basierend auf dem aktuellen Level."""
        for level, duration in self.pauses.items():
            if int(level) > self.current_level:
                return int(level), duration
        return None, 0

    def time_until_next_pause(self):
        """Berechnet die Zeit bis zur nächsten Pause vom aktuellen Level aus."""
        remaining_time = 0
        for i in range(self.current_level, self.total_levels):
            level_info = self.levels[i]
            remaining_time += level_info.get("duration", 0) * 60
            if (i + 1) == self.next_pause_level:
                break
        return remaining_time
    
class Player:
    def __init__(self, name, points=0, rebuys=0, addon=False, bonus=False, bust=False, knockout=False, eliminated_by=""):
        self.name = name
        self.points = points
        self.rebuys = rebuys
        self.addon = addon
        self.bonus = bonus
        self.bust = bust
        self.knockout = knockout
        self.eliminated_by = eliminated_by

    def increase_knockout(self):
        self.knockout = True

    def increase_rebuys(self):
        self.rebuys += 1

    def update_points(self, points):
        self.points = points

    def update_punkte_spieltag(self, punkte):
        self.punkte_spieltag = punkte

    def update_punkte_jahreswertung(self, punkte):
        self.punkte_jahreswertung = punkte

    def toggle_bust(self):
        self.bust = not self.bust

    def toggle_addon(self):
        self.addon = not self.addon

    def toggle_bonus(self):
        self.bonus = not self.bonus

    def set_eliminated_by(self, eliminator_name):
        self.eliminated_by = eliminator_name  # Setzt, wer den Spieler eliminiert hat

    def increase_knockout(self):
        self.knockout += 1

class VariantRoulette:
    def __init__(self, json_file):
        self.json_file = json_file
        self.all_variants = self.load_variants()
        self.available_variants = self.all_variants.copy()

    def load_variants(self):
        try:
            with open(self.json_file, 'r') as file:
                data = json.load(file)
                return data.get("poker_variants", [])
        except FileNotFoundError:
            messagebox.showerror("Error", f"The file {self.json_file} was not found.")
            return []
        except json.JSONDecodeError:
            messagebox.showerror("Error", f"Error decoding {self.json_file}.")
            return []

    def spin(self):
        if not self.available_variants:
            # Alle Varianten wurden gespielt, Liste zurücksetzen
            self.available_variants = self.all_variants.copy()
            messagebox.showinfo("Info", "All variants have been played. Starting over with a full list.")

        # Zufällige Variante auswählen
        selected_variant = random.choice(self.available_variants)
        self.available_variants.remove(selected_variant)
        return selected_variant

class LightningQRCode:
    def __init__(self, parent, address):
        self.parent = parent
        self.address = address

    def generate_qr(self):
        # Erzeuge den QR-Code aus der Adresse
        qr = qrcode.make(self.address)
        return qr

    def show_qr_window(self):
        # Generiere das QR-Bild und öffne ein neues Fenster
        qr_image = self.generate_qr()
        qr_image = qr_image.resize((300, 300), Image.LANCZOS)  # Verwende LANCZOS anstelle von ANTIALIAS
        qr_photo = ImageTk.PhotoImage(qr_image)

        # Neues Fenster für den QR-Code
        qr_window = tk.Toplevel(self.parent)
        qr_window.title("Bitcoin Lightning QR Code")
        qr_window.geometry("350x400")  # Höhe des Fensters leicht vergrößern

        # Label für Spendenhinweis
        donation_label = tk.Label(qr_window, text="Donate to Save Racoons:", font=("Helvetica", 16))
        donation_label.pack(pady=(20, 5))  # Abstand über dem Label

        # QR-Code Label
        qr_label = tk.Label(qr_window, image=qr_photo)
        qr_label.image = qr_photo  # Behalte eine Referenz, damit das Bild nicht gelöscht wird
        qr_label.pack(padx=20, pady=20)

class BountyManager:
    def __init__(self):
        self.bounty_price = 0
        self.total_bounties = {}

    def set_bounty_price(self, price):
        """Setzt den Preis für jeden Bounty."""
        self.bounty_price = price

    def record_knockout(self, player):
        """Erfasst einen Knockout für den Spieler und erhöht den Bounty-Earnings-Wert."""
        if player.name in self.total_bounties:
            self.total_bounties[player.name] += 1
        else:
            self.total_bounties[player.name] = 1

    def calculate_bounty_earnings(self, player):
        """Berechnet die gesamten Bounty-Einnahmen eines Spielers."""
        return self.total_bounties.get(player.name, 0) * self.bounty_price

    def get_total_knockouts(self, player):
        """Gibt die Anzahl der Knockouts des Spielers zurück."""
        return self.total_bounties.get(player.name, 0)

if __name__ == "__main__":
    app = Turniermanager()
    app.mainloop()