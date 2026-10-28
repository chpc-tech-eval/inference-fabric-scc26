export const POST = async ({ cookies, redirect }) => {
  cookies.delete('session', { path: '/' });
  return redirect('/', 303);
};
