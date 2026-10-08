"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { requestCode, verifyCode } from "@/lib/api-client";
import { getDictionary, type Locale } from "@/lib/i18n";
import { safeNext } from "@/lib/navigation";

import styles from "./Forms.module.css";

export function LoginView({ lang }: { lang: Locale }) {
  const dict = getDictionary(lang);
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"), lang);
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [channel, setChannel] = useState("");
  const [resendAt, setResendAt] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (step !== "code") return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [step]);

  async function send(event?: FormEvent) {
    event?.preventDefault();
    setBusy(true);
    setError("");
    try {
      const sent = await requestCode(phone);
      setChannel(sent.channel);
      setResendAt(Date.now() + sent.resend_after * 1000);
      setNow(Date.now());
      setStep("code");
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function confirm(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await verifyCode(phone, code);
      router.replace(next);
      router.refresh();
    } catch (failure) {
      setError((failure as Error).message);
      setBusy(false);
    }
  }

  const wait = Math.max(0, Math.ceil((resendAt - now) / 1000));
  return (
    <div className={`container ${styles.page}`}>
      <h1 className={`display ${styles.title}`}>{dict.login}</h1>
      <p className={styles.lead}>{dict.loginLead}</p>
      <div className={styles.card}>
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        {step === "phone" ? (
          <form onSubmit={send}>
            <div className={styles.field}>
              <label htmlFor="phone">{dict.phone}</label>
              <input id="phone" type="tel" inputMode="tel" autoComplete="tel" required value={phone}
                placeholder={dict.phonePlaceholder} onChange={(event) => setPhone(event.target.value)} />
            </div>
            <button className="button" type="submit" disabled={busy}>
              {busy ? dict.sending : dict.getCode}
            </button>
          </form>
        ) : (
          <form onSubmit={confirm}>
            <p className={styles.success}>{dict.codeSent(channel)}</p>
            <div className={styles.field}>
              <label htmlFor="code">{dict.code}</label>
              <input id="code" className={styles.code} inputMode="numeric" autoComplete="one-time-code" required
                pattern="[0-9]{6}" maxLength={6} value={code} autoFocus
                onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} />
            </div>
            <div className={styles.actions}>
              <button className="button" type="submit" disabled={busy || code.length !== 6}>
                {dict.signIn}
              </button>
              <button className={styles.link} type="button" disabled={wait > 0 || busy} onClick={() => send()}>
                {wait > 0 ? dict.resendIn(wait) : dict.resend}
              </button>
              <button className={styles.link} type="button" onClick={() => { setStep("phone"); setCode(""); setError(""); }}>
                {dict.changePhone}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
