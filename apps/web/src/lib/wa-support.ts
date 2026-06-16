// WhatsApp deep-link for manual upgrade / support flows.
// Billing is manual at MVP (CLAUDE.md decision #18) — the picker opens WA with
// a pre-filled message so the support team can quote + invoice off-platform.

const DEFAULT_NUMBER = '6281234567890';

function getNumber(): string {
  const v = import.meta.env.VITE_SUPPORT_WA_NUMBER;
  return typeof v === 'string' && v.length > 0 ? v : DEFAULT_NUMBER;
}

export function openUpgradeChat(workspaceName: string, planLabel: string): void {
  const text = encodeURIComponent(
    `Halo, saya mau upgrade workspace "${workspaceName}" ke plan ${planLabel}. Mohon info pembayarannya, terima kasih.`,
  );
  window.open(
    `https://wa.me/${getNumber()}?text=${text}`,
    '_blank',
    'noopener,noreferrer',
  );
}
