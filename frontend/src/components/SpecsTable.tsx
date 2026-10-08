import { formatValue, type AttrValue } from "@/lib/format";
import { localized, type Locale } from "@/lib/i18n";
import type { AttributeDefinition } from "@/lib/schemas";

import styles from "./SpecsTable.module.css";

export function SpecsTable({
  definitions,
  values,
  lang,
}: {
  definitions: AttributeDefinition[];
  values: Record<string, AttrValue>;
  lang: Locale;
}) {
  const rows = definitions.filter((definition) => values[definition.code] !== undefined);
  if (rows.length === 0) return null;
  return (
    <dl className={styles.specs}>
      {rows.map((definition) => (
        <div key={definition.code} className={styles.row}>
          <dt>{localized(definition, lang)}</dt>
          <dd>{formatValue(values[definition.code], definition.unit, lang)}</dd>
        </div>
      ))}
    </dl>
  );
}
