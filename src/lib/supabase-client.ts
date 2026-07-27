import { createClient } from "@supabase/supabase-js";

// New Supabase project credentials
const supabaseUrl = "https://lakbvdmjtoarmxmzvynu.supabase.co";
const supabaseAnonKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI5MDMwNjcsImV4cCI6MjA5ODQ3OTA2N30.Uy5pmvNr0_kEiOb1-hZ1zjiV0DgHbAVYdC-FB6vTjmc";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
