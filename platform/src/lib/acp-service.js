// One shared ACP client, created on first use. If the ACP is not configured (secret not mounted,
// a setting missing) the rest of the website keeps working and the staff page says so plainly.
import { AcpClient, configFromEnv } from './acp.js';

let client = null;
let failed = false;

export function getAcp() {
  if (client) return { acp: client };
  if (failed) return { acp: null };
  try {
    client = new AcpClient(configFromEnv());
    return { acp: client };
  } catch (e) {
    failed = true; // restart the pod after fixing the configuration
    console.error('ACP client not configured:', e.message); // names settings/paths only, never values
    return { acp: null };
  }
}
