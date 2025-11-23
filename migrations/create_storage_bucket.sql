-- Create the storage bucket for event posters if it doesn't exist
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'event-posters', 
  'event-posters', 
  true,
  10485760, -- 10MB
  '{image/jpeg,image/jpg,image/png,image/webp,image/gif}'
)
on conflict (id) do update set
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Safely create policies (drop if exists first)
drop policy if exists "Public Access" on storage.objects;
create policy "Public Access"
  on storage.objects for select
  using ( bucket_id = 'event-posters' );

drop policy if exists "Authenticated Users can upload" on storage.objects;
create policy "Authenticated Users can upload"
  on storage.objects for insert
  with check ( bucket_id = 'event-posters' and auth.role() = 'authenticated' );

drop policy if exists "Users can update own files" on storage.objects;
create policy "Users can update own files"
  on storage.objects for update
  using ( bucket_id = 'event-posters' and auth.uid() = owner )
  with check ( bucket_id = 'event-posters' and auth.uid() = owner );

drop policy if exists "Users can delete own files" on storage.objects;
create policy "Users can delete own files"
  on storage.objects for delete
  using ( bucket_id = 'event-posters' and auth.uid() = owner );
