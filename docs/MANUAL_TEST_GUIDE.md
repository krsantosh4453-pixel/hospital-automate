# Manual test guide (har role se login karke check karna)

Ye guide aapke apne computer par, development server par, har role se login
karke ye dekhne ke liye hai ki kaun sa kaam sahi chal raha hai. Saara data
**synthetic** hai, ek alag "Demo City Hospital" mein. Aapka asli data nahi
chhua jaata.

## 1. Server chalaayein (do Terminal tabs)

Terminal 1 — backend:

```bash
cd "/Users/santoshkumar/Desktop/hospital automate/backend"
source venv/bin/activate
python manage.py migrate
python manage.py seed_demo --password "Apna-Password-123"
python manage.py runserver
```

- `"Apna-Password-123"` ki jagah apna koi bhi password likhein (kam se kam
  10 akshar). **Saare demo logins isi password se khulenge.** Command
  password kabhi screen par print nahi karti.
- `seed_demo` dobara chalaane se kuch duplicate nahi hota; password badal
  jaata hai.
- Ye command sirf development (`DEBUG=True`) par chalti hai; production par
  mana kar deti hai.

Terminal 2 — frontend:

```bash
cd "/Users/santoshkumar/Desktop/hospital automate"
npm run dev
```

Browser mein kholein: http://localhost:5173

> Project iCloud (Desktop) mein hai; agar koi command atak jaaye to
> project ko iCloud se bahar (jaise `~/hospital-automate`) copy karke wahan
> chalaayein.

## 2. Demo logins

| Login | Kahan | Role | Kya hona chahiye |
|---|---|---|---|
| `demo.admin` | Staff sign in | Admin | Sab kuch dikhe |
| `demo.doctor1` | Staff sign in | Doctor, Cardiology (Dr Asha Mehta) | Sirf apne 2 patients |
| `demo.doctor2` | Staff sign in | Doctor, Orthopaedics (Dr Rohan Verma) | Sirf apne 2 patients |
| `demo.nurse` | Staff sign in | Nurse (aaj Ward A, Morning duty) | Ward A + aaj ki OPD queue |
| `demo.desk` | Staff sign in | Receptionist, Cardiology | Sirf Cardiology queue |
| `demo.desk.main` | Staff sign in | Receptionist, koi department nahi | Poori queue |
| `demo.patient@example.test` | Patient sign in → **Email** tab | Patient | Apni booking |

Staff logins par mobile number set nahi hai, isliye OTP nahi maanga jaata —
seedha password se login hota hai. Har login ke baad header ke hospital
selector mein **Demo City Hospital** chunein.

Demo data:

| Patient | Kiska | Kahan |
|---|---|---|
| Demo Ravi (Cardiology OPD) | Dr Asha Mehta | Aaj ki OPD queue, token #1 |
| Demo Sunil (Ortho OPD) | Dr Rohan Verma | Aaj ki OPD queue, token #2 |
| Demo Kiran (Ward A) | Dr Asha Mehta | Admitted, Ward A |
| Demo Meena (Ward B) | Dr Rohan Verma | Admitted, Ward B |
| Demo Portal Patient | — | Patient portal ka apna account |

## 3. Check-list (har line par ✅ ya ❌ lagaayein)

### Public page (bina login)
- [ ] http://localhost:5173 par public page; sirf **Book appointment**,
      koi Add button nahi; figures ki jagah "—".
- [ ] Kisi department tile par click → "You are not eligible for this work".

### Patient (`demo.patient@example.test`)
- [ ] Public page → **Book appointment** → Email tab se login → seedha
      booking form khule.
- [ ] Doctor, kal ki date, free time chunein → **Confirm booking** →
      "Booked with …" message aur list mein appointment.
- [ ] Wahi slot dobara book karne par wo time list mein na dikhe.

### Doctor (`demo.doctor1`)
- [ ] Home par counts sirf apne (pending appointments 1).
- [ ] **Patients**: sirf Demo Ravi aur Demo Kiran; Sunil/Meena nahi.
- [ ] **Queue** → **Call next patient**: sirf apna token (Ravi) bule.

### Nurse (`demo.nurse`)
- [ ] **Patients**: Demo Kiran (Ward A) + aaj ki OPD (Ravi, Sunil);
      Demo Meena (Ward B) nahi.
- [ ] Admin se duty Cancel karwaane ke baad (neeche) Demo Kiran gayab ho.

### Receptionist
- [ ] `demo.desk` → **Queue**: sirf Demo Ravi (Cardiology).
- [ ] `demo.desk.main` → **Queue**: Ravi aur Sunil dono.

### Admin (`demo.admin`)
- [ ] **Patients**: saare demo patients.
- [ ] **Administration → Nurse duty**: Nurse Priya, Ward A, Morning dikhe;
      **Cancel** dabaayein → nurse se dobara check karein.
- [ ] **Administration → Users**: `demo.desk.main` ka Department
      "Orthopaedics" karein → us login se Queue mein sirf Sunil.
- [ ] **Doctors** page par kisi doctor ko Edit → "Login email" field dikhe.

### Galat login
- [ ] Galat password → "Invalid credentials." message, login nahi.
- [ ] Lagaatar kai baar galat password → "Too many failed sign-in attempts…"
      (15 minute ka lock; `seed_demo` dobara chalaane se password reset hota hai,
      lock nahi).

## 4. Kaam khatam hone par demo data hataayein

```bash
cd "/Users/santoshkumar/Desktop/hospital automate/backend"
source venv/bin/activate
python manage.py seed_demo --remove
```

Ye sirf "Demo City Hospital" aur `demo.` se shuru hone wale logins hataata
hai; baaki data ko haath nahi lagaata.

## Agar kuch ❌ ho

Kaunsi line ❌ hui, kis login se, aur screen par kya message aaya — ye bata
dein (screenshot bhi chalega). Password kabhi chat mein na bhejein.
