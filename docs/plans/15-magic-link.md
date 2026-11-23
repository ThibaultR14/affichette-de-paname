# Plan #15 - Connexion par magic link

## Constat
- Le trigger `on_auth_user_created` (création du profil) existe déjà dans `20261122000000_init.sql` et il est testé dans `supabase/tests/rls.test.sql` (« trigger: one profile per new user », lecture du profil par son propriétaire). Rien à changer côté schéma.
- Le client `supabase` (`lib/supabase.ts`) garde ses réglages par défaut : session dans `localStorage`, rafraîchissement auto, `detectSessionInUrl`.

## Choix
- **Flux implicite** (défaut de supabase-js), pas PKCE : sur mobile, le lien du mail s'ouvre souvent dans un autre navigateur que celui de la demande (appli mail → navigateur intégré). Avec PKCE, la connexion échouerait dans ce cas.
- `emailRedirectTo = <origin>/connexion` : on revient sur la page de connexion, qui affiche soit « c'est bon, on t'a reconnu », soit l'erreur du lien (expiré, déjà utilisé) lue dans le hash `#error_code=otp_expired…`.
- Pas d'état global (contexte) : un hook `useSession()` abonné à `onAuthStateChange`. Assez pour l'en-tête et la page.

## Fichiers
- `web/src/lib/auth.ts` : `useSession()` (`undefined` pendant le chargement, `null` = déconnecté, `Session`), `sendMagicLink(email)`, `signOut()` (`scope: 'local'`), `readLinkError(hash, search)` (lien expiré ou en échec, lu dans le hash ou la query).
- `web/src/pages/LoginPage.tsx` + `.css` : route `/connexion`.
  - déconnecté : titre « connexion », « on t'envoie un lien par mail, pas de mot de passe. », champ email, bouton « envoie-moi le lien ».
  - envoyé : « c'est parti. regarde tes mails (et les spams), le lien marche une heure. » + « pas reçu ? recommencer ».
  - erreurs : email invalide, trop de demandes (429 : « doucement, réessaie dans une minute. »), lien expiré, client absent.
  - connecté : « c'est bon, on t'a reconnu : <email>. » + lien « voir les séances » + bouton « se déconnecter ».
- `web/src/components/AccountBar.tsx` : rendue par `Root` en haut de toutes les pages sauf `/connexion`, « connexion » (lien) ou « <email> · se déconnecter ».
- `web/src/lib/router.ts` : route `{ page: 'login' }` pour `/connexion`. `Root.tsx` charge la page à la demande.
- `supabase/templates/magic_link.html` et `confirmation.html` : mails en français, sobres (texte + lien, ton du site). Objets : « ton lien pour l'affichette de paname » / « confirme ton adresse (l'affichette de paname) ».
- `supabase/config.toml` : `[auth.email.template.magic_link]` et `[auth.email.template.confirmation]` ; `site_url` et `additional_redirect_urls` passent au port 5180 (le dev de ce site).
- Docs : `architecture.md` (route, auth), `decisions.md` (flux implicite, retour sur /connexion), `design.md` (le `localStorage` garde aussi la session Supabase, ce n'est plus la « seule donnée stockée »).

## Tests (d'abord)
- `router.test.tsx` : `/connexion` et `/connexion/` → `login`.
- `auth.test.ts` : `useSession`, `readLinkError` (otp_expired, autre code, pas d'erreur) ; `sendMagicLink` appelle `signInWithOtp` avec `emailRedirectTo` sur `/connexion` et `shouldCreateUser: true` (client mocké).
- `LoginPage.test.tsx` (client mocké) : envoi → état « regarde tes mails » ; 429 → message ; erreur dans le hash → message et hash nettoyé ; session → email affiché, « se déconnecter » appelle `signOut`.
- `AccountBar.test.tsx` : lien « connexion » sans session, email + déconnexion avec session.
- pgTAP : déjà couvert, on relance `npx supabase test db`.

## À faire à la main (projet cloud)
- Dashboard Supabase → Authentication → URL Configuration : `Site URL` = l'URL Pages, redirections autorisées : `https://<projet>.pages.dev/connexion`, `https://*.<projet>.pages.dev/connexion` (previews), `http://localhost:5180/connexion`. Sans l'entrée des previews, le lien retombe sur `Site URL` : la connexion marche quand même, mais l'erreur d'un lien expiré n'est affichée nulle part.
- Authentication → Email Templates : coller les deux gabarits (pas de `config push`, qui écraserait `site_url` avec la valeur locale).
- Envoi de mails : le SMTP par défaut de Supabase est limité (quelques mails/heure), suffisant pour tester. Le SMTP Resend viendra avec les alertes.

## Hors scope
- Favoris (issues suivantes), suppression de compte RGPD, SMTP Resend, connexion par code OTP à 6 chiffres.
