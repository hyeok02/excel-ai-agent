import ManagedUserTable from '@/components/admin/users/ManagedUserTable'
import UserAccountForm from '@/components/admin/users/UserAccountForm'
import useUserManagement from '@/hooks/admin/useUserManagement'

const UserManagementPage = () => {
  const { error, form, handleSubmit, isLoading, isSubmitting, setForm, success, users } =
    useUserManagement()

  return (
    <div className="space-y-7">
      <div className="page-heading">
        <div>
          <p className="eyebrow">ACCESS MANAGEMENT</p>
          <h1 className="page-title">사용자 관리</h1>
          <p className="page-description">
            사내 계정을 발급하고 시스템 접근 권한을 관리합니다.
          </p>
        </div>
        <div className="status-pill" data-status="success">
          <span /> 사용자 {users.length}명
        </div>
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[24rem_1fr]">
        <UserAccountForm
          error={error}
          form={form}
          isSubmitting={isSubmitting}
          onFormChange={setForm}
          onSubmit={handleSubmit}
          success={success}
        />
        <ManagedUserTable isLoading={isLoading} users={users} />
      </div>
    </div>
  )
}

export default UserManagementPage
