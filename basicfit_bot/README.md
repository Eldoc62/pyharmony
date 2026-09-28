# BasicFit Auto-Booking Bot

Bot qui surveille en continu la disponibilité d'un créneau à 5h30 les
lundi/mardi/jeudi/vendredi au club Petite Synthe, réserve automatiquement
dès que c'est disponible, notifie par Telegram, puis s'arrête.

## ⚠️ À lire avant de déployer

1. **Risque CGU** : automatiser la réservation BasicFit viole probablement
   leurs conditions d'utilisation. BasicFit a déjà envoyé une mise en
   demeure DMCA à un projet similaire (janvier 2026). Usage personnel sur
   ton propre compte = risque modéré, mais pas nul (blocage de compte
   possible s'ils détectent l'automatisation).
2. **Endpoints non vérifiés** : `basicfit_client.py` reconstruit les appels
   API à partir d'un projet open-source de 2021 (`my.basic-fit.com`).
   L'interface actuelle (`member.basic-fit.com/booking`) a changé de
   domaine depuis, donc ces chemins sont probablement à ajuster. **Ne
   déploie pas le bot en continu avant d'avoir validé avec
   `test_connection.py`** (voir plus bas).

## 1. Créer le bot Telegram

1. Dans Telegram, ouvre une conversation avec **@BotFather**.
2. Envoie `/newbot`, choisis un nom et un nom d'utilisateur (doit finir par
   `bot`).
3. BotFather te donne un **token** (format `123456789:AA...`) — c'est
   `TELEGRAM_BOT_TOKEN`.
4. Envoie n'importe quel message à ton nouveau bot (pour qu'il "connaisse"
   ta conversation).
5. Va sur `https://api.telegram.org/bot<TON_TOKEN>/getUpdates` dans un
   navigateur, remplace `<TON_TOKEN>` par ton token. Cherche
   `"chat":{"id":...}` dans la réponse JSON — c'est ton
   `TELEGRAM_CHAT_ID`.

## 2. Valider la connexion à BasicFit (obligatoire avant déploiement)

```bash
cd /volume1/scripts/basicfit-bot
mkdir -p config logs
cp config.example.txt config/credentials.txt
nano config/credentials.txt   # remplis email/mot de passe/token/chat_id
chmod 600 config/credentials.txt

pip3 install -r requirements.txt   # ou python3 -m pip install -r requirements.txt

python3 test_connection.py
```

- Si ça affiche `club_id` et une liste de créneaux en JSON : les endpoints
  fonctionnent, tu peux déployer.
- Si tu as une erreur HTTP (401/404/etc.) : les endpoints ont changé. Il
  faut capturer les vraies requêtes :
  1. Ouvre `https://member.basic-fit.com/booking/fr-FR` dans Chrome/Firefox,
     connecte-toi.
  2. Ouvre les DevTools (F12) → onglet **Réseau/Network** → coche
     "Preserve log" → filtre sur **Fetch/XHR**.
  3. Recharge la page, navigue jusqu'au planning d'un jour, regarde les
     créneaux.
  4. Repère les requêtes de login, de récupération du planning, et (si tu
     fais un vrai test de réservation) de réservation.
  5. Clic droit sur chacune → **Copy as cURL**, colle-moi le résultat (en
     masquant ton mot de passe) pour que j'ajuste `basicfit_client.py`.

## 3. Déploiement sur le Synology (DSM Task Scheduler)

Copie tout le dossier `basicfit_bot/` sur le NAS, par exemple dans
`/volume1/scripts/basicfit-bot/`.

**Tâche 1 — lancement au démarrage :**
- Panneau de configuration → Planificateur de tâches → Créer → Tâche
  déclenchée → Script défini par l'utilisateur.
- Événement : **Démarrage**.
- Utilisateur : celui qui a les droits sur le dossier.
- Script :
  ```bash
  bash /volume1/scripts/basicfit-bot/deploy/start.sh
  ```

**Tâche 2 — supervision (relance si crash) :**
- Créer → Tâche planifiée → Script défini par l'utilisateur.
- Planification : toutes les 15 ou 30 minutes.
- Script :
  ```bash
  bash /volume1/scripts/basicfit-bot/deploy/supervisor.sh
  ```

Rends les scripts exécutables une fois copiés :
```bash
chmod +x deploy/start.sh deploy/supervisor.sh
```

## 4. Lancement manuel (alternative pour tester)

```bash
cd /volume1/scripts/basicfit-bot
python3 main.py
```

`Ctrl+C` pour arrêter. Les logs sont dans `logs/basicfit_bot.log` (avec
rotation automatique).

## Structure

- `main.py` — boucle principale (scrape toutes les ~30s, réserve, notifie, s'arrête).
- `basicfit_client.py` — appels HTTP vers BasicFit (⚠️ à valider, voir plus haut).
- `scheduling.py` — calcule les prochains lundi/mardi/jeudi/vendredi à l'heure cible.
- `telegram_notifier.py` — envoi de la notification de confirmation.
- `config.py` / `config.example.txt` — chargement des identifiants et réglages.
- `logger_setup.py` — logs fichier (avec rotation) + console.
- `test_connection.py` — script de validation manuelle (voir section 2).
- `deploy/` — scripts pour le Task Scheduler DSM.
