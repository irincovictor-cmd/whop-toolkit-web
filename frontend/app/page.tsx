import { redirect } from "next/navigation";
import { getSession } from "@/lib/whop-session";

export default async function Home() {
  const session = await getSession();
  redirect(session ? "/dashboard" : "/login");
}
