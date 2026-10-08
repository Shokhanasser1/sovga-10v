"use client";

import Form from "next/form";
import type { ReactNode } from "react";

/** GET-форма фильтров: галочки и сортировка применяются сразу, цена — по кнопке. */
export function AutoSubmitForm({
  action,
  className,
  children,
}: {
  action: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Form
      action={action}
      className={className}
      onChange={(event) => {
        const target = event.target;
        if (target instanceof HTMLInputElement && target.type === "number") return;
        event.currentTarget.requestSubmit();
      }}
    >
      {children}
    </Form>
  );
}
