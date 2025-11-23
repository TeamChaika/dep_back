-- Allow public read access to active events
drop policy if exists "Public can view active events" on events;
create policy "Public can view active events"
  on events for select
  using ( is_deleted = false );

-- Allow public read access to active establishments (needed for event details)
drop policy if exists "Public can view active establishments" on establishments;
create policy "Public can view active establishments"
  on establishments for select
  using ( is_deleted = false );

